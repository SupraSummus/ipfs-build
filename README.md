IPFS-build
==========

It is a little tool to help publish absolutely linked content to IPFS.

Examples
--------

### References between files

`a.md` file:

    some content blabla

`index.md` file that contains link to `a.md`:

    [here](/ipfs/--a-md--) is the `a.md`

`.ipfs_build.json` build description:

    {"sources": {
        "index.md": {
            "--a-md--": {
                "type": "ref",
                "source": "a.md"
            }
        }
    }}

Build command:

    cd path/to/project
    ipfs_build.py

### Constant refs

Lets say you have a MD document (`index.md`) that links to already
published document. One option is to hardcode target hash in new
document:

    look [here](/ipfs/QmSrCRJmzE4zE1nAfWPbzVfanKQNBhp7ZWmMnEdbiLvYNh)!

With IPFS-build you can do:

    look [here](/ipfs/||md-reader-example||)!

And configure substituted value in `.ipfs_build.json`:

    {"sources": {
        "index.md": {
            "||md-reader-example||": {
                "type": "const",
                "value": "QmSrCRJmzE4zE1nAfWPbzVfanKQNBhp7ZWmMnEdbiLvYNh"
            }
        }
    }}

### Building for targets

When you don't want to get flooded with lots of hashes you can specify
targets. Only them and their dependecies will be built, and only their
hashes will be shown.

`.ipfs_build.json`:

    {
        "sources": {
            // lots of sources
        },
        "targets": [
            "index.html",
            "main.js",
            "style.css"
        ]
    }

### Defining builds in python

`from ipfs_build import *` and rock!

Example at `examples/raw/test.py`.
