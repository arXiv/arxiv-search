# with import <nixpkgs> { config = {
#   packageOverrides = pkgs: {
#     uwsgi = pkgs.uwsgi.override { xlibs = null; }; # how to make this enable pcre?
#   };
# };};
with import <nixpkgs> {};
with pkgs.python36Packages;
stdenv.mkDerivation {
  name = "impurePythonEnv";
  buildInputs = [
    gcc6
    docker-compose
    mysql80
    ncurses

    # these packages are required for virtualenv and pip to work:
    #
    mypy
    python36Full
    python36Packages.virtualenv
    
    python36Packages.numpy
  ];
  src = null;
  # TODO: convert to full nix expression so as to not rely on pip
  shellHook = ''
    export NIX_ENFORCE_PURITY=0
    # set SOURCE_DATE_EPOCH so that we can use python wheels
    SOURCE_DATE_EPOCH=$(date +%s)
    export LANG=en_US.UTF-8
    virtualenv venv
    source venv/bin/activate
    export PATH=$PWD/venv/bin:$PATH
    export PYTHONPATH=$PWD:$PYTHONPATH
    export LD_LIBRARY_PATH=${mysql57}/lib:${gcc6.cc.lib}/lib:$LD_LIBRARY_PATH
    export FLASK_APP=app.py
    export FLASK_DEBUG=1

    pip install pipenv
    pipenv --three install --dev
  '';
}
