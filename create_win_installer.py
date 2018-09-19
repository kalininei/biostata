import os
import os.path
import subprocess
import shutil

pyfile = os.path.join(os.curdir, 'biostata.py')
if not os.path.exists(pyfile):
    raise Exception("The script should be run within project root directory")

if os.name != 'nt':
    raise Exception("The script should be run on windows platform only")

# get version number
fn = os.path.join(os.curdir, 'prog', 'bopts.py')
fid = open(fn, 'r')
_version = None
for line in fid.readlines():
    if line.find('_version = ') >= 0:
        exec(line)
        break
fid.close()
if _version is None:
    raise Exception("Failed to detect version from prog/bopts.py file")
print("Detected version is ", _version)

# write version number to nsi file
fn = os.path.join(os.curdir, 'make_installer.nsi')
fid = open(fn, 'r')
lines = fid.readlines()
fid.close()

for i, line in enumerate(lines):
    if line.find('!define VERSION ') >= 0:
        lines[i] = '!define VERSION "{}"\r\n'.format(_version)
        break
else:
    raise Exception("Version string was not found in make_installer.nsi")

fid = open(fn, 'w')
fid.writelines(lines)
fid.close()

# run pyinstaller
subprocess.call(["python", "-OO", "-m", "PyInstaller",
                 "-y", "-w", "--clean", "-i"
                 '{}'.format(os.path.join(os.curdir,
                                          'resources',
                                          'biostata256.ico')),
                 "biostata.py"])
# rename biostata.exe to Biostata.exe
shutil.move('dist\\biostata\\biostata.exe', 'dist\\biostata\\Biostata.exe')

# run nsis
subprocess.call(["C:\\Program Files (x86)\\NSIS\\makensis.exe",
                 "make_installer.nsi"])
