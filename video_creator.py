from reddit_lib import PostWithComments
from google.cloud import texttospeech
import os
import numpy as np
from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    concatenate_videoclips,
    CompositeVideoClip,
    CompositeAudioClip,
    AudioFileClip
)
import asyncio
import cv2
import youtube_lib
import random
from moviepy.audio.fx import audio_normalize, audio_fadein, audio_fadeout, volumex
from pydub import AudioSegment
import re


# voices: https://cloud.google.com/text-to-speech/docs/voices
def text_to_ssml_break_after_questions(text):
    # Replace question marks with break tags
    text = re.sub(r'\?', '?<break time="500ms"/>', text)
    # Wrap text with SSML tags
    ssml = f'<speak>{text}</speak>'
    return ssml


def preprocess_text(text):
    link_pattern = re.compile(r'\[(.*?)\]\(.*?\)')

    # Replace each link with just the text inside the square brackets
    text_without_links = link_pattern.sub(r'\1', text)
    # remove any https://www. or http://www.
    text_without_links = text_without_links.replace("https://www.", "")
    text_without_links = text_without_links.replace("http://www.", "")
    text_without_links = text_without_links.replace("https://", "")
    for site_end in ['com', 'ca', 'org', 'net']:
        text_without_links = text_without_links.replace(f".{site_end}/", f".{site_end}")

    # replace r/anything with r slash anything
    pattern = r'r/(\w+)'
    replacement = r'r slash \1'
    # Replace all occurrences of "r/[anything]" with "r slash anything"
    new_text = re.sub(pattern, replacement, text_without_links)

    pattern = r'\bOP\b'
    replacement = 'oh pee'

    # Replace all occurrences of "OP" with "oh pee"
    new_text = re.sub(pattern, replacement, new_text)

    # remove all * from bolding
    new_text = new_text.replace("*", "")

    return new_text


def tts(text, output_file):
    """Use GCP text to speech to make an mp3 file from text."""
    client = texttospeech.TextToSpeechClient()
    # if "?" in text:
    #     text = text_to_ssml_break_after_questions(text)
    #     synthesis_input = texttospeech.SynthesisInput(ssml=text)
    # else:
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", name="en-US-Studio-M")
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=1.2,
        effects_profile_id=['handset-class-device'])
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    if os.path.exists(output_file):
        os.remove(output_file)
    with open(output_file, "wb") as out:
        # Write the response to the output file.
        out.write(response.audio_content)
        print(f'Audio content written to file {output_file}')


def make_mp3s(post_with_comments):
    """Use tts function to make mp3 for the post and each comment. Return a list of the mp3 filenames."""
    post_id = post_with_comments.post.post_id
    mp3s = []

    audio_path = os.path.join(os.getcwd(), "audio")
    post_mp3 = f"{post_id}.mp3"
    post_path = os.path.join(audio_path, post_mp3)
    tts(post_with_comments.post.text, post_path)
    mp3s.append(post_path)

    comments = post_with_comments.comments
    for comment in comments:
        text = comment.text
        text = preprocess_text(text)
        comment_mp3 = f"{post_id}_{comment.comment_id}.mp3"
        comment_path = os.path.join(audio_path, comment_mp3)
        tts(text, comment_path)
        mp3s.append(comment_path)
    return mp3s


def get_all_image_paths(post_with_comments: PostWithComments):
    """Return a list of all the png paths for the post and comments."""

    png_paths = []
    png_paths.append(post_with_comments.post.path_to_image)

    comments = post_with_comments.comments
    for comment in comments:
        png_paths.append(comment.path_to_image)
    return png_paths


def create_video(image_paths, audio_paths, padding_time: float = 1.0) -> CompositeVideoClip:
    """
    Given a list of image paths and a list of audio paths, create a video using
    moviepy.editor. Each image will be displayed for the duration of the
    corresponding audio clip, with padding between each clip (during which the image is still visible).
    """
    clips = []
    for i, (image_path, audio_path) in enumerate(zip(image_paths, audio_paths)):
        # Load image and audio clips
        image_clip = ImageClip(image_path)
        audio_clip = AudioFileClip(audio_path)

        # Set the duration of the image clip to the duration of the audio clip
        image_clip = image_clip.set_duration(audio_clip.duration)

        audio_clip = audio_fadeout.audio_fadeout(audio_clip, 0.1)

        # Combine the image and audio clips
        clip = image_clip.set_audio(audio_clip)

        # Add the clip to the list
        clips.append(clip)

    # Combine all clips into a single video
    video = concatenate_videoclips(clips)

    return video


def add_music(video_path, music_dir):
    """
    Add random lofi backing track to video. Normalize audio so it isn't overpowering.

    :param video_path: path of original video
    :return:
    """
    print("Adding music...")
    audio_options = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
    mp3_file = random.choice(audio_options)
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(os.path.join(music_dir, mp3_file))
    normalized_audio_clip = audio_normalize.audio_normalize(audio_clip)
    normalized_audio_clip = volumex.volumex(normalized_audio_clip, 0.05)
    video_duration = video_clip.duration
    min_start_time = 30.0  # first 30 seconds are build up in most music
    max_start_time = normalized_audio_clip.duration - video_duration
    start_time = random.uniform(min_start_time, max_start_time)
    end_time = start_time + video_duration
    print(f"Chose {mp3_file} from {start_time} - {end_time}")
    audio_segment = normalized_audio_clip.subclip(start_time, end_time)
    audio_segment = audio_fadein.audio_fadein(audio_segment, 1)
    audio_segment = audio_fadeout.audio_fadeout(audio_segment, 1)

    final_audio_clip = CompositeAudioClip([video_clip.audio, audio_segment])
    final_clip = video_clip.set_audio(final_audio_clip)

    new_file_name = video_path.replace(".mp4", "_with_music.mp4")
    if os.path.exists(new_file_name):
        os.remove(new_file_name)
    final_clip.write_videofile(new_file_name, codec="libx264", audio_codec="aac", fps=30)
    print("Done adding music!")
    return new_file_name


def resize_maintain_aspect_ratio(image, width):
    """
    Resize an image to a new width while maintaining the aspect ratio.
    """
    # Get the original image size
    (h, w) = image.shape[:2]

    # Calculate the ratio of the new image width to the old image width
    r = width / float(w)

    # Resize the image
    dim = (width, int(h * r))
    resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

    # Return the resized image
    return resized


def add_background_to_images(image_paths, background_path):
    """
    Given a list of image paths and a background image path, add each image to the background image and save the result.
    - Also trims the top of the comment images to hide the "single comment thread" text
    - Also deletes the original image_paths paths

    :param image_paths: list of paths to images
    :param background_path: path of background image, should be 1080w x1920h
    :return: paths to the new images on backgrounds
    """
    print("Adding images to background...")
    bg_paths = []
    for index, image_path in enumerate(image_paths):
        img = cv2.imread(image_path)
        img = resize_maintain_aspect_ratio(img, 750)
        if index != 0:
            # trim the top to hide the "single comment thread"
            img = img[75:, :, :]
        bg = cv2.imread(background_path)
        # center the image over the background, which is 1080 wide and 1920 tall
        x_offset = 1080 // 2 - img.shape[1] // 2
        y_offset = 1920 // 2 - img.shape[0] // 2
        bg[y_offset:y_offset + img.shape[0], x_offset:x_offset + img.shape[1]] = img
        # get original path and append _bg to the end
        bg_path = image_path[:-4] + "_bg.png"
        cv2.imwrite(bg_path, bg)
        bg_paths.append(bg_path)
    for path in image_paths:
        os.remove(path)
    return bg_paths


def add_silence_to_mp3s(mp3_paths):
    return_list = []
    for mp3_path in mp3_paths:
        audio_file = AudioSegment.from_file(mp3_path, format="mp3")

        # Add 1 second of silence to the end of the audio file
        silence = AudioSegment.silent(duration=700)  # 1000ms = 1s
        audio_file = audio_file + silence

        export_path = mp3_path[:-4] + "_with_silence.mp3"
        # Export the new audio file with the added silence
        audio_file.export(export_path, format="mp3")
        return_list.append(export_path)
    return return_list


def make_video_from_post_with_comments(post_with_comments: PostWithComments):
    if isinstance(post_with_comments, asyncio.Future):
        post_with_comments = post_with_comments.result()
    if post_with_comments is None:
        return
    print(f"3. Making video for post {post_with_comments.post.post_id}...")

    audio_paths = make_mp3s(post_with_comments)
    audio_paths = add_silence_to_mp3s(audio_paths)

    image_paths = get_all_image_paths(post_with_comments)
    print(image_paths)
    image_w_bg_paths = add_background_to_images(image_paths, "background.png")
    video_clip = create_video(image_w_bg_paths, audio_paths)

    video_path = os.path.join(os.getcwd(), "videos", f"{post_with_comments.post.post_id}.mp4")
    if os.path.exists(video_path):
        os.remove(video_path)
    video_clip.write_videofile(video_path, codec="libx264", audio_codec="aac", fps=30)
    print(f"Done making video for {post_with_comments.post.post_id}, output to {video_path}")

    music_dir = os.path.join(os.getcwd(), "music")
    final_video_path = add_music(video_path, music_dir)
    return final_video_path


def make_and_post_video(post_with_comments: PostWithComments):
    """
    Given a PostWithComments object, make a video showing the pictures of the post, followed by the comments,
    all with voiceover.

    :return: path to video if succeeded, or None otherwise
    """
    final_video_path = make_video_from_post_with_comments(post_with_comments)

    if post_with_comments.subreddit.lower() == "askreddit":
        try:
            print("Posting to youtube...")
            youtube_lib.upload_to_askreddit_channel(final_video_path, post_with_comments.post.text)
        except Exception as e:
            print(f"Error uploading to youtube: {e}")


if __name__ == '__main__':
    youtube_lib.upload_to_askreddit_channel(r'K:\Big_Pycharm_Projects\ReddYT\videos\129k7ok.mp4',
                                            "What's the first sign that a movie is going to be bad?")
    pass
