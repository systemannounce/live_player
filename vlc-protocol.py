import sys
import subprocess

def main(argv):
    command = argv[0][:-16] + 'vlc.exe -vv --extraintf=logger ' + argv[1][6:]
    print(command)
    subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

if __name__ == '__main__':
    main(sys.argv)
