!/bin/bash

##
# Configure here if you want
PV_DEV=""                   # Space delimited device list
VGNAME=""                   # Will create this VG if it doesn't exist
NODES=""                    # (short) host name
DOMAIN=""                   # If there's a domain in the node names 
MKLVS="Y"                   # Make the Linux LVs
CREATE_STORAGECLASSES="Y"   # Create requesite storage classes

while getopts ":n:v:" opt; do
  case ${opt} in
    n )
        # Comma delimited list of nodes
        NODES=$OPTARG
        ;;
    v )
        # Name of volume group to create
        VGNAME=$OPTARG
        ;;
    p )
        # Physical device list to include in volume group
        PV_DEV=$OPTARG
        ;;
    m )
        # Skip volume creation all together
        MKLVS='N'
        ;;
    s )
        # Skip storage class creation
        CREATE_STORAGECLASSES='N'
        ;;
    d )
        # Add a domain
        DOMAIN=$OPTARG
        if [ "$DOMAIN" != "" ]; then
            $DOMAIN=".${DOMAIN}"
        fi
        ;;
    \? )
        echo "Usage: cmd [-n:] [-v:] [-p:] [-d:] [-m] [-s]"
        echo "  -n  comma-delimited list of short node names (not fully qualified)"
        echo "  -d  if kube node names include a domain, add it here"
        echo "  -v  name of volume group to create on each host"
        echo "  -p  space-delimited (use quotes) physical device list. If this is"
        echo "      different on each host then you will need create the volume"
        echo "      groups by hand and use the -m flag here to skip volume group"
        echo "      creation."
        echo "  -m  skip volume group creation"
        echo "  -s  skip creation of storage classes"
        ;;
  esac
done

if [ "$MKVLS" = "Y" ]; then
    DIE=0
    [ "$VGNAME" = "" ] || DIE="a VG name"
    [ "$PV_DEV" = "" ] || DIE="a PV list"
    if [ "$DIE" != "0" ]; then
        echo "you're missing ${DIE}, exiting"
        exit 1
    fi

    if [ -d "/dev/${VGNAME}" && "$MKLVS" = "Y" ]; then
        echo "volume group \"${VGNAME}\" exists, skipping volume creation "
        MKLVS="N"
    fi
fi

if [ "$NODES" = "" ]; then
    echo "You need a node list"
    exit 1
fi

##
# Some default names
LV_MONGO="zenko-mongo"
LV_PROMETHEUS="zenko-prometheus"
LV_REDIS="zenko-redis"
LV_QUORUM="zenko-quorum"
LV_S3_DATA="zenko-s3-data"
LV_QUEUE="zenko-queue"
LV_MGOB="zenko-mgob"
LV_BURRY="zenko-burry"

if [ "$CREATE_STORAGECLASSES" == "Y" ]; then
    kubectl apply -f ./storage_classes.yaml
fi

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

    ./mkvol.py vols.yaml ${n}-${LV_MONGO} ${n}${DOMAIN} ${LV_MONGO} /dev/$VGNAME/${LV_MONGO}
    ./mkvol.py vols.yaml ${n}-${LV_PROMETHEUS} ${n}${DOMAIN} ${LV_PROMETHEUS} /dev/$VGNAME/${LV_PROMETHEUS}
    ./mkvol.py vols.yaml ${n}-${LV_REDIS} ${n}${DOMAIN} ${LV_REDIS} /dev/$VGNAME/${LV_REDIS}
    ./mkvol.py vols.yaml ${n}-${LV_QUORUM} ${n}${DOMAIN} ${LV_QUORUM} /dev/$VGNAME/${LV_QUORUM}
    ./mkvol.py vols.yaml ${n}-${LV_S3_DATA} ${n}${DOMAIN} ${LV_S3_DATA} /dev/$VGNAME/${LV_S3_DATA}
    ./mkvol.py vols.yaml ${n}-${LV_QUEUE} ${n}${DOMAIN} ${LV_QUEUE} /dev/$VGNAME/${LV_QUEUE}
    ./mkvol.py vols.yaml ${n}-${LV_MGOB} ${n}${DOMAIN} ${LV_MGOB} /dev/$VGNAME/${LV_MGOB}
    ./mkvol.py vols.yaml ${n}-${LV_BURRY} ${n}${DOMAIN} ${LV_BURRY} /dev/$VGNAME/${LV_BURRY}

done
