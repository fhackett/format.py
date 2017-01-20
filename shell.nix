with import <nixpkgs> {};
  stdenv.mkDerivation{
    name = "pythonEnv";
    shellHook = ''
      rm -rf .venv pyvenv.cfg format.egg-info
      mkdir .venv
      pyvenv .venv
      source .venv/bin/activate
      pip install pytest
      python setup.py develop
    '';
    buildInputs = [ python3 ];
  }
