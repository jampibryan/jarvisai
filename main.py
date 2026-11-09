from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from app.assistant import JarvisAssistant
from app.config import AppConfig


def main() -> None:
    parser = argparse.ArgumentParser(description='JarvisAI assistant')
    parser.add_argument('--create-shortcut', action='store_true', help='Create the Windows shortcut with the Jarvis icon')
    parser.add_argument('--desktop', action='store_true', help='Open the hands-free desktop interface')
    parser.add_argument('--voice', dest='mode', action='store_const', const='voice', help='Start the assistant in voice mode')
    parser.add_argument('--text', dest='mode', action='store_const', const='text', help='Start the assistant in text mode')
    parser.add_argument('--safe-mode', dest='safe_mode', action='store_true', help='Simulate dangerous actions instead of executing them')
    parser.add_argument('--unsafe-mode', dest='safe_mode', action='store_false', help='Allow dangerous actions to run for real')
    parser.add_argument('--confirm-dangerous', dest='confirm_dangerous_actions', action='store_true', help='Require confirmation before shutdown or restart')
    parser.add_argument('--no-confirm-dangerous', dest='confirm_dangerous_actions', action='store_false', help='Run shutdown or restart without confirmation')
    parser.add_argument('--tts', dest='enable_tts', action='store_true', help='Enable text-to-speech responses')
    parser.add_argument('--no-tts', dest='enable_tts', action='store_false', help='Disable text-to-speech responses')
    parser.add_argument('--wake-word', dest='voice_wake_word', help='Word required before executing a spoken command')
    parser.add_argument('--require-wake-word', dest='voice_require_wake_word', action='store_true', help='Require the wake word before spoken commands')
    parser.add_argument('--no-wake-word', dest='voice_require_wake_word', action='store_false', help='Accept spoken commands without wake word')
    parser.add_argument('--continuous', dest='voice_continuous', action='store_true', help='Continuous, hands-free voice mode')
    parser.add_argument('--no-continuous', dest='voice_continuous', action='store_false', help='Push-to-talk voice mode')
    parser.add_argument('--voice-rate', dest='voice_rate', type=int, help='Text-to-speech speed rate (words per minute)')
    parser.add_argument('--apply-file-changes', action='store_true', help='Apply confirmed changes to files selected in Explorer')
    parser.set_defaults(
        mode=None,
        safe_mode=None,
        confirm_dangerous_actions=None,
        enable_tts=None,
        voice_require_wake_word=None,
        voice_wake_word=None,
        voice_continuous=None,
        voice_rate=None
    )
    args = parser.parse_args()

    if args.create_shortcut:
        from app.ui.shortcut import create_shortcut

        create_shortcut(Path(__file__).resolve().parent)
        return

    config = AppConfig.load()
    overrides = {}
    if args.mode is not None:
        overrides['input_mode'] = args.mode
    if args.safe_mode is not None:
        overrides['safe_mode'] = args.safe_mode
    if args.confirm_dangerous_actions is not None:
        overrides['confirm_dangerous_actions'] = args.confirm_dangerous_actions
    if args.enable_tts is not None:
        overrides['enable_tts'] = args.enable_tts
    if args.voice_require_wake_word is not None:
        overrides['voice_require_wake_word'] = args.voice_require_wake_word
    if args.voice_wake_word is not None:
        overrides['voice_wake_word'] = args.voice_wake_word
    if args.voice_continuous is not None:
        overrides['voice_continuous'] = args.voice_continuous
    if args.voice_rate is not None:
        overrides['voice_rate'] = args.voice_rate
    if args.apply_file_changes:
        overrides['apply_file_changes'] = True

    if overrides:
        config = replace(config, **overrides)

    config.ensure_runtime_paths()
    if args.desktop:
        from app.ui.desktop import JarvisDesktop, create_desktop_root

        desktop_config = replace(config, input_mode='voice', voice_continuous=True)
        JarvisDesktop(create_desktop_root(), desktop_config).run()
        return
    assistant = JarvisAssistant(config)
    assistant.run(mode=args.mode)


if __name__ == "__main__":
    main()
