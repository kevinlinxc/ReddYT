from reddit_lib import PostWithComments
from google.cloud import texttospeech
import os
import numpy as np
from moviepy.editor import (
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
        audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=1,
        effects_profile_id=['headset-class-device'])
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

        # Add padding time to the end of the clip (with last frame still visible)
        if i != len(image_paths) - 1:
            image_clip = image_clip.set_end(image_clip.end + padding_time)

        # Combine the image and audio clips
        clip = image_clip.set_audio(audio_clip)

        # Add the clip to the list
        clips.append(clip)

    # Combine all clips into a single video
    video = concatenate_videoclips(clips)

    return video


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


def add_to_background(image_paths, background_path):
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
        img = resize_maintain_aspect_ratio(img, 900)
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


def create_random_colour_background(output_name):
    """
    Create a 1080 x 1920 background png with a random colour. It should be a bright colour to attract viewers.
    Made using HSV in OpenCV, one solid colour, saved to output_name.
    """
    img = np.zeros((1920, 1080, 3), np.uint8)
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
    image_w_bg_paths = add_to_background(image_paths, "background.png")
    video_clip = create_video(image_w_bg_paths, audio_paths)

    video_path = os.path.join(os.getcwd(), "videos", f"{post_with_comments.post.post_id}.mp4")
    video_clip.write_videofile(video_path, codec="libx264", audio_codec="aac", fps=30)
    print(f"Done making video for {post_with_comments.post.post_id}, output to {video_path}")


if __name__ == '__main__':
    pass
