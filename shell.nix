with import <nixpkgs> {};
  stdenv.mkDerivation{
    name = "pythonEnv";
    shellHook = ''
      rm -rf .venv pyvenv.cfg format.egg-info
      mkdir .venv
      python3 -m venv .venv
      source .venv/bin/activate
      pip install pytest
      python setup.py develop
    '';
    buildInputs = [ python36 ];
  }
