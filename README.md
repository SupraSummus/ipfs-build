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
            "type": "replace",
            "replace": {
                "--a-md--": "a.md"
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
            "type": "replace",
            "replace": {
                "||md-reader-example||": "md-reader"
            }
        },
        "md-reader": {"type": "static", "product_id": "QmSrCRJmzE4zE1nAfWPbzVfanKQNBhp7ZWmMnEdbiLvYNh"}
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

### Replace refs by regexp

File `blabla_a`:

    blablabla

File `blabla_b`:

    blablable

File `index`:

    load(a) a b a b
    load(b) b a b a

`.ipfs_build.json`:

    {
        "sources": {
            "index": {
                "type": "regexp",
                "pattern": "load\\(([^\\)]+)\\)",
                "replacement": "load(ipfs({}))",
                "source": "blabla_{}"
            }
        }
    }

### Reuse a source

    {
        "source_types": {
            "mysource": {
                // source definition
            }
        },
        "sources": {
            "index": {"type": "source_type", "name": "mysource"},
            "other_file": {"type": "source_type", "name": "mysource"}
        }
    }

### Use wildcards

    {
        "sources": {
            "src/**/*.js": {...},
            "style/*.css": {...}
        }
    }

### Defining builds in python

`from ipfs_build import *` and rock!

Examples at `test/**/test.py`.
