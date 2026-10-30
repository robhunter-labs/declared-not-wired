# Declared, Not Wired — a four-route example

**Status: Built, not exercised.** A runnable synthetic example with its own tests; it hasn't been run against any real agent framework. Companion to [*Declared, Not Wired*](https://robhunterworks.com/writing/declared-not-wired/). More studies are indexed in [ai-security-field-lab](https://github.com/robhunter-labs/ai-security-field-lab).

An approval check can exist in a system without standing between every route and the effect it is meant to control. This small Python example makes that difference visible at one in-memory receiver.

The four local routes represent a function tool, a hosted-tool stand-in, a specialist handoff, and a recovery step. Each runs twice: once with a matching approval token and once without it. The receiver, not the route's own status label, determines whether the effect occurred. An optional all-wired run puts the same approval check in front of every route and gives the detector a conformant comparison.

There is no network, provider SDK, external message, real target, or platform emulator. These are deliberately small stand-ins for a path-inspection method, not a security product or a claim about any named agent framework. The known path list is complete only for this tiny example.

The companion essay, [*Declared, Not Wired*](https://robhunterworks.com/writing/declared-not-wired/), explains the original assumption, the correction to the first detector, the relevant prior art, and how to apply the question to a real system without mistaking this example for platform coverage.

## Run it

Python 3.9 or newer, standard library only.

```sh
python3 demo.py --classify                 # four path states; three routes are nonconforming
python3 demo.py --all-wired --classify     # approval before every effect; all four conformant
python3 demo.py                            # the underlying ordered events
python3 validate_assay.py fixture.json     # classify the checked-in fixture
python3 -m unittest -v                     # receiver tests plus every detector case (hostile ones included)
```

`VALID` means the local fixture passed its checks; `CONFORMANT` means every listed route enforced approval before the effect. One does not imply the other. Malformed input (not a JSON object, a path that isn't an object, and so on) classifies as `INVALID` with a defect code rather than crashing.

The assay's `fixture.json` is a synthetic registered-path fixture. It is not a trace from a real agent runtime. Its twins and evidence match what `demo.py` generates (a test checks this); its descriptive metadata (assay id, receiver name, discovery methods) is the hand-written registered form and differs on purpose. `validate_assay.py` checks each twin's ordered local events and outcome rather than trusting a declared state label or an aggregate event list alone. The first detector trusted failure labels; this version also refuses a false green when an allowed run bypasses the control or reaches it after the effect. It still knows only the four paths in this example.

Copyright © 2026 Rob Hunter. Original code is released under the MIT license in `LICENSE`; references to third-party frameworks in the essay are for context, not an affiliation or validation claim.
