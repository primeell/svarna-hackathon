"""
Project SVARNA — Main Entry Point
====================================
Run the full pipeline from command line.
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.core.pipeline import SVARNAPipeline


def main():
    parser = argparse.ArgumentParser(
        description="SVARNA — AI-Powered Agricultural Supply Chain Intelligence"
    )
    parser.add_argument(
        "--audio", "-a",
        type=str,
        default=None,
        help="Path to farmer's voice note audio file",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="AgentConfig.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run with mock data (no audio file needed)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Save pipeline results to JSON file",
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = SVARNAPipeline(config_path=args.config)

    # Run
    if args.mock:
        results = pipeline.run(audio_file=None)
    elif args.audio:
        results = pipeline.run(audio_file=args.audio)
    else:
        print("Usage: python main.py --mock  OR  python main.py --audio <file.wav>")
        print("Run with --help for all options.")
        sys.exit(1)

    # Output
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        print(f"\n[OK] Results saved to {out_path}")
    else:
        print("\n" + "=" * 60)
        print("SVARNA Pipeline Results")
        print("=" * 60)
        print(json.dumps(results, indent=2, default=str, ensure_ascii=False))

    # Print alerts summary
    alerts = pipeline.get_alerts()
    if alerts:
        print(f"\n[ALERT] Economic Alerts: {len(alerts)}")
        for alert_entry in alerts:
            payload = alert_entry.get("payload", {})
            title = payload.get("title", "")
            if title:
                print(f"  - {title}")

    print(f"\nBlackboard Stats: {pipeline.get_stats()}")


if __name__ == "__main__":
    main()
