import os

if hasattr(os,'uname'):
    system = os.uname()[0]
else:
    system = 'Windows'

# install location
AddOption('--prefix',
          dest='prefix',
          type='string',
          nargs=1,
          action='store',
          metavar='DIR',
          help='installation prefix')
# debug flags for compliation
debug = ARGUMENTS.get('debug',1)

if not GetOption('prefix')==None:
    install_prefix = GetOption('prefix')
else:
    install_prefix = '/usr/local/'

Help("""
Type: 'scons test' to build test programs
      'scons install' to install libraries and headers under %s
      (use --prefix  to change library installation location)
      (NB: python package is installed with setup.py)

Options:
      debug=0      to disable debug compliation
""" % install_prefix)


env = Environment(ENV = os.environ,
                  CCFLAGS=['-Wall'],
                  LIBS=['hdf5','hdf5_hl'],
                  CPPPATH=['c++'], # only used for compiling test
                  PREFIX=install_prefix,
                  tools=['default'])

if system=='Darwin':
    env.Append(CPPPATH=['/opt/local/include'],
               LIBPATH=['/opt/local/lib'])
if int(debug):
    env.Append(CCFLAGS=['-g2'])
else:
    env.Append(CCFLAGS=['-O2'])

env.Alias('install',env.Install(os.path.join(env['PREFIX'],'include'), 'c++/arf.hpp'))
env.Alias('install', env.Install(os.path.join(env['PREFIX'],'include','arf'),env.Glob('c++/arf/*.hpp')))

test = [env.Program(os.path.splitext(str(x))[0], [x]) \
            for x in env.Glob('tests/*.cpp') if str(x).startswith('test')]
env.Alias('test',test)


