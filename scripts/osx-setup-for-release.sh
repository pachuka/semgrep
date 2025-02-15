#!/usr/bin/env bash
set -eux

# Setup the environment under MacOS to build and release semgrep-core.

# history: there used to be a separate osx-m1-release.sh script
# that was mostly a copy of this file, but now the
# build steps are identical so we just have one script.

# Note that this script runs from a self-hosted CI runner which
# does not reset the environment between each run, so you may
# need to do more cleanup than usually necessary.

brew install opam
#still needed?
#brew update
#still needed?
#opam init --no-setup --bare

# Some CI runners have tree-sitter preinstalled which interfere with
# out static linking plans below so better to remove it.
# TODO: fix setup-m1-builder.sh instead?
brew uninstall --force tree-sitter

#coupling: this should be the same version than in our Dockerfile
if opam switch 4.14.0 ; then
    # This happens because the self-hosted CI runners do not
    # cleanup things between each run.
    echo "Switch 4.14.0 exists, continuing"
else
    echo "Switch 4.14.0 doesn't yet exist, creating..."
    opam switch create 4.14.0
    opam switch 4.14.0
fi
eval "$(opam env)"

#pad:??? What was for? This was set only for the M1 build before
# Needed so we don't make config w/ sudo
export HOMEBREW_SYSTEM=1

make install-deps-MACOS-for-semgrep-core
make install-deps-for-semgrep-core

# Remove dynamically linked libraries to force MacOS to use static ones.
ls -l "$(brew --prefix)"/opt/pcre/lib || true
ls -l "$(brew --prefix)"/opt/gmp/lib || true
rm -f "$(brew --prefix)"/opt/pcre/lib/libpcre.1.dylib
rm -f "$(brew --prefix)"/opt/gmp/lib/libgmp.10.dylib

# This needs to be done after make install-deps-xxx but before make core
TREESITTER_LIBDIR=libs/ocaml-tree-sitter-core/tree-sitter/lib
echo "TREESITTER_LIBDIR is $TREESITTER_LIBDIR and contains:"
ls -l "$TREESITTER_LIBDIR" || true

echo "Deleting all the tree-sitter dynamic libraries to force static linking."
rm -f "$TREESITTER_LIBDIR"/libtree-sitter.0.0.dylib
rm -f "$TREESITTER_LIBDIR"/libtree-sitter.0.dylib
rm -f "$TREESITTER_LIBDIR"/libtree-sitter.dylib
