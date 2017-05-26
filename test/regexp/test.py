from ipfs_build import *

build_and_print(IPFSEnvironment({
    'index': IPFSRegexpSource(
        pattern=b'load\\(\'([^\']*)\\.code\'\\)',
        replacement=b'load(\'/ipfs/{}\')',
        source='prefix_{}_sufix'
    ),
    'prefix_a_sufix': StaticSource(b'nukes'),
    'prefix_b_sufix': StaticSource(b'codes'),
}))
