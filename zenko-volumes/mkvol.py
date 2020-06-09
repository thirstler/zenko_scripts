#!/usr/bin/python3

import sys,os

try: sys.argv[1]
except:
    print("give me something to work with here!")
    sys.exit(1)

with open(sys.argv[1], 'r') as fh:
    template = fh.read()
fh.close()

template = template.replace("%VOLUME_NAME%", sys.argv[2])
template = template.replace("%NODE_NAME%", sys.argv[3])
template = template.replace("%STORAGE_CLASS_NAME%", sys.argv[4])
template = template.replace("%DEVICE_PATH%", sys.argv[5])

with open("/tmp/v.yml", 'w') as fh:
    fh.write(template)
fh.close()

cmd = "kubectl apply -f /tmp/v.yml"

os.system(cmd)
