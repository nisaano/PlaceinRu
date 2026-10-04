"""Train and evaluate the experimental MRT-AI RuBERT multi-label classifier."""
import argparse
import json

from mrt_ai.nlp.intent.training import train


def main() -> None:
    parser = argparse.ArgumentParser(description="Train MRT-AI's experimental Misha intent classifier.")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.learning_rate <= 0:
        parser.error("epochs, batch-size and learning-rate must be positive.")
    print(json.dumps(train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
