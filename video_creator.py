from reddit_lib import PostWithComments
from google.cloud import texttospeech
import os
import numpy as np
from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    concatenate_videoclips,
    CompositeVideoClip,
    AudioFileClip
)
import asyncio
import cv2
# voices: https://cloud.google.com/text-to-speech/docs/voices


def tts(text, output_file):
    """Use GCP text to speech to make an mp3 file from text."""
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", name="en-US-Studio-M")
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=1, effects_profile_id=['medium-bluetooth-speaker-class-device'])
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
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
    if os.path.exists(post_path):
        print(f"TTS file already exists for {post_id}, skipping")
    else:
        tts(post_with_comments.post.text, post_path)
    mp3s.append(post_path)

    comments = post_with_comments.comments
    for comment in comments:
        text = comment.text
        comment_mp3 = f"{post_id}_{comment.comment_id}.mp3"
        comment_path = os.path.join(audio_path, comment_mp3)
        if os.path.exists(comment_path):
            print(f"TTS file already exists for {post_id}_{comment.comment_id}, skipping")
        else:
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


from moviepy.editor import *
import os


def create_video(image_paths, audio_paths, padding_time: float = 1.0) -> CompositeVideoClip:
    """
    Given a list of image paths and a list of audio paths, create a video using
    moviepy.editor. Each image will be displayed for the duration of the
    corresponding audio clip, overlaid over a centered background image, and there will be a constant padding time
    between each clip.
    """

    clips = []

    # Add image with corresponding audio
    print(image_paths, audio_paths)
    for i, image_path in enumerate(image_paths):
        audio_path = audio_paths[i]
        if os.path.exists(image_path) and os.path.exists(audio_path):
            image_clip = ImageClip(image_path).set_duration(AudioFileClip(audio_path).duration)
            audio_clip = AudioFileClip(audio_path)
            clips.append(image_clip.set_audio(audio_clip))

            # Add padding time between each clip
            if i > 0:
                clips.append( ColorClip((1080, 1920), color=[255, 255, 255]).set_duration(padding_time))

    # Calculate the position of each image in the video

    max_height = max([clip.h for clip in clips])
    x_pos = 1080//2 # center x position of the images
    y_pos = 1920//2 # center y position of the images
    y_offset = (max_height-y_pos)//2 # offset for vertical positioning
    y_positions = [(y_pos - clip.h//2 - y_offset) for clip in clips]

    # Create a video with the centered background image and overlaid clips
    background_image = "background.png"

    background = ImageClip(background_image).set_duration(sum([clip.duration for clip in clips]))
    clips = [clip.set_position((x_pos, y_positions[i])) for i, clip in enumerate(clips)]
    final_clip = CompositeVideoClip([background] + clips, size=(1080, 1920)).set_fps(30)

    return final_clip


def create_random_colour_background(output_name):
    """
    Create a 1080 x 1920 background png with a random colour. It should be a bright colour to attract viewers.
    Made using HSV in OpenCV, one solid colour, saved to output_name.
    """
    img = np.zeros((1080, 1920, 3), np.uint8)
    sat = np.random.randint(200, 255)
    val = np.random.randint(200, 255)
    hue = np.random.randint(0, 179)
    # convert hsv to bgr
    img[:] = cv2.cvtColor(np.array([[[hue, sat, val]]], dtype=np.uint8), cv2.COLOR_HSV2BGR)
    cv2.imwrite(output_name, img)


def make_and_post_video(post_with_comments: PostWithComments):
    """
    Given a PostWithComments object, make a video showing the pictures of the post, followed by the comments,
    all with voiceover.

    :return: path to video if succeeded, or None otherwise
    """
    if post_with_comments is None:
        return
    if isinstance(post_with_comments, asyncio.Future):
        post_with_comments = post_with_comments.result()
    print(f"3. Making video for post {post_with_comments.post.post_id}...")

    audio_paths = make_mp3s(post_with_comments)
    image_paths = get_all_image_paths(post_with_comments)
    create_random_colour_background(os.path.join(os.getcwd(), "background.png"))
    video_clip = create_video(image_paths, audio_paths)

    video_path = os.path.join(os.getcwd(), "videos", f"{post_with_comments.post.post_id}.mp4")
    video_clip.write_videofile(video_path, codec="libx264", audio_codec="aac")
    print(f"Done making video for {post_with_comments.post.post_id}, output to {video_path}")


if __name__ == '__main__':
    pass





