#!/bin/bash

MKLVS="Y"             # Make the Linux LVs
PV_DEV="/dev/vdb1"    # Space delimited device list
VGNAME="metalvg"      # Will create this VG if it doesn't exist
NODES="metal-01 metal-02 metal-03" # (short) host name

# Use DOMAIN if domain is part of node names
DOMAIN="galaxy.lab" 
#DOMAIN=""

LV_MONGO="zenko-mongo"
LV_PROMETHEUS="zenko-prometheus"
LV_REDIS="zenko-redis"
LV_QUORUM="zenko-quorum"
LV_S3_DATA="zenko-s3-data"
LV_QUEUE="zenko-queue"
LV_MGOB="zenko-mgob"
LV_BURRY="zenko-burry"

for n in ${NODES}; do

    if [ "$MKLVS" == "Y" ]; then
        ssh ${n} "pvcreate $PV_DEV &> /dev/null"
        ssh ${n} "vgcreate $VGNAME $PV_DEV  &> /dev/null"
        ssh ${n} "lvcreate -n ${LV_MONGO} -L 50G $VGNAME"
        ssh ${n} "lvcreate -n ${LV_PROMETHEUS} -L 8G $VGNAME"
        ssh ${n} "lvcreate -n ${LV_REDIS} -L 10G $VGNAME"
        ssh ${n} "lvcreate -n ${LV_QUORUM} -L 5G $VGNAME"
        ssh ${n} "lvcreate -n ${LV_S3_DATA} -L 5G $VGNAME"
        ssh ${n} "lvcreate -n ${LV_QUEUE} -L 20G $VGNAME"
        ssh ${n} "lvcreate -n ${LV_MGOB} -L 10G $VGNAME"
        ssh ${n} "lvcreate -n ${LV_BURRY} -L 1G $VGNAME"
    fi

    ./mkvol.py vols.yaml ${n}-${LV_MONGO} ${n}.${DOMAIN} ${LV_MONGO} /dev/$VGNAME/${LV_MONGO}
    ./mkvol.py vols.yaml ${n}-${LV_PROMETHEUS} ${n}.${DOMAIN} ${LV_PROMETHEUS} /dev/$VGNAME/${LV_PROMETHEUS}
    ./mkvol.py vols.yaml ${n}-${LV_REDIS} ${n}.${DOMAIN} ${LV_REDIS} /dev/$VGNAME/${LV_REDIS}
    ./mkvol.py vols.yaml ${n}-${LV_QUORUM} ${n}.${DOMAIN} ${LV_QUORUM} /dev/$VGNAME/${LV_QUORUM}
    ./mkvol.py vols.yaml ${n}-${LV_S3_DATA} ${n}.${DOMAIN} ${LV_S3_DATA} /dev/$VGNAME/${LV_S3_DATA}
    ./mkvol.py vols.yaml ${n}-${LV_QUEUE} ${n}.${DOMAIN} ${LV_QUEUE} /dev/$VGNAME/${LV_QUEUE}
    ./mkvol.py vols.yaml ${n}-${LV_MGOB} ${n}.${DOMAIN} ${LV_MGOB} /dev/$VGNAME/${LV_MGOB}
    ./mkvol.py vols.yaml ${n}-${LV_BURRY} ${n}.${DOMAIN} ${LV_BURRY} /dev/$VGNAME/${LV_BURRY}

done
