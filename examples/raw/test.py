from ipfs_build import *

environment = PathBasedIPFSEnvironment({
    'two_values': Source({
        b'//a value//': ConstantFiller(b'42'),
    }),
    'index': Source({
        b'//two values file//': SourceReferenceFiller('./two_values'),
        b'//static file//': SourceReferenceFiller('static_file'),
        b'//whole dir//': SourceReferenceFiller('dir'),
    }),
    'dir/in_dir_file': Source({
        b'//two values//': SourceReferenceFiller('two_values'),
    }),
}, targets=['index'])

if __name__ == '__main__':
    result = environment.build()
    PathBasedIPFSEnvironment.print_result(result)
