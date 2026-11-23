# Expressive Africa TTS: vocalisation dataset

This branch adds a **data and training research track** for eight integrated vocal behaviours:
- `sigh`, `sniff`, `laughter`, `breathing`, `gasp`, `whisper`, `throat_clear`, `groan`.

The goal is one voice-conditioned model that can produce an event and continue speaking in the same reference voice. These are **not** post-mixed sound effects.

## Important model constraint

The released six-layer model and its tokenizer were not trained with these event controls. Writing `[sigh]` in a prompt will not make the released checkpoint synthesize a sigh. A working integrated model requires all of the following:

1. Consented, licensed audio with accurate event and speech annotations.
2. Event-aware text tokenization (reserved control symbols) and compatible embedding initialization.
3. Event-aware training examples and loss masks; non-speech vocalisations must not be sent through the ordinary word aligner.
4. Whispered speech examples with transcripts and a whisper style span.
5. Fine-tuning of the 24-layer Africa teacher while preserving the existing voice-prompt conditioning, followed by evaluation and only then student distillation.
6. Regression tests for normal speech, voice similarity, event quality, and event-to-speech transitions.

The existing training loader derives target text from word alignments and chooses a voice prompt from the same recording. Do not pass event-only clips into that loader as if they were ordinary aligned speech. The event-aware loader must explicitly handle event boundaries and clips without lexical words.

## Annotation format

Create a UTF-8 JSONL file with one object per recording. Required fields:

```json
{
  "audio": "audio/speaker_001/session_01.wav",
  "transcript": "I do not think this will work.",
  "language": "eng",
  "speaker_id": "speaker_001",
  "split": "train",
  "license": "CC-BY-4.0",
  "consent": true,
  "events": [
    {"type": "sigh", "start": 0.0, "end": 1.1, "position": "before"}
  ]
}
```

- `start` and `end` are seconds relative to the beginning of the audio.
- `position` is optional descriptive context: `before`, `during`, or `after`. The timestamps remain authoritative.
- For whispering, annotate the exact whispered speech span with `type: "whisper"`; the transcript must contain the words spoken in that span.
- A clip may contain multiple events. Events must not overlap unless the overlap is real and deliberately annotated.
- `transcript` may be empty only for a purely non-verbal clip.
- Keep speakers grouped in a single split; do not leak the same speaker across train/validation/test.
- Keep original audio, source URL, attribution, consent evidence, and licence terms in your dataset records. Do not redistribute material whose licence forbids it.

## Validate annotations

```bash
python recipes/africa/expressive/validate_manifest.py annotations.jsonl --audio-root /path/to/dataset
```

The validator checks schema, event names, timestamps, split names, consent/licence metadata, audio existence, and speaker leakage. It does not download audio or certify that a licence permits model training.

## Initial dataset coverage

Aim for balanced, clean examples per event and speaker, plus ordinary speech from the same speakers. Public vocalisation datasets can bootstrap event discovery, but verify the exact licence and source consent before training. Whispering needs dedicated whispered speech with transcripts; ordinary speech relabelled as whisper is not valid training data. Sigh/sniff/breath/gasp/laughter/throat-clear/groan examples should include varied intensity, duration, and conversational context.

## Training status

This branch currently defines the annotation contract and validator only. It does **not** yet change the model, tokenizer, inference API, or SONIVOX deployment. The next engineering stage is to implement the event-aware tokenizer and loader together, then add teacher fine-tuning. Do not advertise an expressive checkpoint until it has actually been trained and evaluated.
