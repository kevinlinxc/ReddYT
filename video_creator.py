from reddit_lib import PostWithComments
from google.cloud import texttospeech
# voices: https://cloud.google.com/text-to-speech/docs/voices


def tts(text, output_file):
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


def make_video(post_with_comments: PostWithComments):
    """
    Given a PostWithComments object, make a video showing the pictures of the post, followed by the comments,
    all with voiceover.

    :return: path to video if succeeded, or None otherwise
    """

    # comments = post_with_comments.comments
    # for comment in comments:
    #     text = comment.text
    #     wav = tts.tts(text, speaker='male-en-2', language='en')
    pass

make_video(None)





