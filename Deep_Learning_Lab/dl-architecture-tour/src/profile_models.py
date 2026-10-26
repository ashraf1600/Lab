"""Count parameters and forward-pass FLOPs for one sample of each architecture.

  python -m src.profile_models
"""
import json
from pathlib import Path

import torch
from torch.utils.flop_counter import FlopCounterMode

from src.data import NOTE_LEN, SEQ_LEN, build_vocab
from src.models import build_model, count_parameters

LENGTHS = [16, 32, 64, 128, 256]


def count_flops(model, x):
    with FlopCounterMode(display=False) as counter:
        model(x)
    return counter.get_total_flops()


def sample(name, length):
    if name == "cnn":
        return torch.zeros(1, 1, 8, 8)
    if name == "lstm":
        return torch.zeros(1, length, 1)
    return torch.full((1, length), 2, dtype=torch.long)  # any real (non-pad) token id


def main():
    torch.manual_seed(42)
    vocab_size = len(build_vocab())
    models = {name: build_model(name, vocab_size).eval() for name in ("cnn", "lstm", "transformer")}
    default_len = {"cnn": None, "lstm": SEQ_LEN, "transformer": NOTE_LEN}
    report = {"models": {}, "seq_scaling": {"lengths": LENGTHS}}

    with torch.no_grad():
        print("{:<12} {:<14} {:>10} {:>14}".format("model", "input", "params", "FLOPs/sample"))
        for name, model in models.items():
            x = sample(name, default_len[name])
            flops = count_flops(model, x)
            params = count_parameters(model)
            report["models"][name] = {"params": params, "flops_per_sample": flops, "input_shape": list(x.shape)}
            print("{:<12} {:<14} {:>10,} {:>14,}".format(name, str(tuple(x.shape)), params, flops))

        for name in ("lstm", "transformer"):
            report["seq_scaling"][name] = [count_flops(models[name], sample(name, n)) for n in LENGTHS]
        print()
        print("FLOPs per sample vs sequence length:")
        print("{:>8} {:>14} {:>14}".format("length", "lstm", "transformer"))
        for i, n in enumerate(LENGTHS):
            print("{:>8} {:>14,} {:>14,}".format(n, report["seq_scaling"]["lstm"][i], report["seq_scaling"]["transformer"][i]))

    out = Path("outputs")
    out.mkdir(exist_ok=True)
    (out / "profile.json").write_text(json.dumps(report, indent=2))
    print("saved -> outputs/profile.json")


if __name__ == "__main__":
    main()
