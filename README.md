# Declared, Not Wired: A four-route example

**Status: Checked on the included synthetic fixture.** A runnable example with its own tests: the first command below shows the expected result in about a second. It uses no network, provider SDK, external message, real target, or platform emulator, and it hasn't been run against any real agent framework, so it says nothing about one. Companion to [*Declared, Not Wired*](https://robhunterworks.com/writing/declared-not-wired/). More studies are indexed in [ai-security-field-lab](https://github.com/robhunter-labs/ai-security-field-lab).

When someone tells me a guardrail is on, the follow-up I've learned to ask is: on which path, before which effect, and how do you know? I learned it from my own early work with agents. If I had described a control clearly and the build could show me where that control lived, I sometimes treated the behavior as present without following every path far enough to prove the system used it.

An approval check can exist in a system without standing between every route and the effect it is meant to control. This small Python example makes that difference visible at one in-memory receiver. Of its four local routes, only the function tool enforces approval before the effect. The other three each show a different way a check can be present and still not stop anything:

- **The route skips the check.** The hosted-tool stand-in reaches the effect without passing through approval (`PATH_UNMEDIATED`).
- **The check only warns.** The specialist handoff records a warning when approval is missing, and the effect happens anyway (`WARN_ONLY`).
- **The check runs too late.** The recovery step evaluates the run only after the effect has already occurred (`EVALUATED_POST_EFFECT`).

Each route runs twice: once with a matching approval token and once without it. The receiver, not the route's own status label, determines whether the effect occurred, so each route is judged by what reached the receiver rather than by what it reports. An optional all-wired run puts the same approval check in front of every route and gives the detector a conformant comparison.

These are deliberately small stand-ins for a path-inspection method, not a security product or a claim about any named agent framework. The known path list is complete only for this tiny example.

## Run it

Python 3.9 or newer, standard library only.

```sh
python3 demo.py --classify                 # four path states; three routes are nonconforming
python3 demo.py --all-wired --classify     # approval before every effect; all four conformant
python3 demo.py                            # the underlying ordered events
python3 validate_assay.py fixture.json     # classify the checked-in fixture
python3 -m unittest -v                     # 5 receiver tests plus 16 detector cases run as subtests
python3 test_assay.py                      # lists each detector case: 16/16, 13 hostile
```

**Start with the first command.** You should see `"validation": "VALID"`, `"conformance": "NON_CONFORMANT"`, and one finding for each of the three routes above. Add `--all-wired` and all four turn conformant.

`VALID` means the local fixture passed its checks; `CONFORMANT` means every listed route enforced approval before the effect. One does not imply the other. Malformed input (not a JSON object, a path that isn't an object, and so on) classifies as `INVALID` with a defect code rather than crashing, which is why a well-formed run shows an empty `defects` list.

`fixture.json` is a synthetic registered-path fixture, not a trace from a real agent runtime. Its paired runs (one with approval, one without; called *twins* in the code) and evidence match what `demo.py` generates, and a test checks this; its descriptive metadata is the hand-written registered form and differs on purpose. `validate_assay.py` checks each twin's ordered local events and outcome rather than trusting a declared state label or an aggregate event list alone, so it refuses a false green when an allowed run bypasses the control or reaches it after the effect. It still knows only the four paths in this example.

Copyright © 2026 Rob Hunter. Original code is released under the MIT license in `LICENSE`; references to third-party frameworks in the essay are for context, not an affiliation or validation claim.

Found a route this misses, or a framework where the question lands differently? [Open an issue](https://github.com/robhunter-labs/declared-not-wired/issues); that is where corrections and questions live. For anything sensitive, use the route in [SECURITY.md](SECURITY.md). I'd like to hear it.
