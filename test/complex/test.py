from ipfs_build import *

slash_slash = IPFSRegexpSource(pattern=b'//(([^/]|/[^/])*)//')

build_and_print(IPFSEnvironment({
    'a value': StaticSource(b'42'),
    'two_values': slash_slash,
    'index': slash_slash,
    'dir/in_dir_file': slash_slash,
}, targets=['index']))
