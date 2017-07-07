# format.py

The current working state of a serializer/deserializer/record library designed to make implementing the JAUS protocol easier.

It contains a partial implementation of the JAUS protocol.

Status:
- the judp transport is functional
- core service state machines are mostly supported
- some of the mobility services are also present

TODO:
- Test against more existing implementations
- Add proper docstrings

To develop on Nix, type `nix-shell`.
For everywhere else, setup.py works as normal.
