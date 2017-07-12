# Base Python image has most up to date Python parts
FROM libatomsquip/quip-base

MAINTAINER Tom Daff "tdd20@cam.ac.uk"

# QUIP compilation - OpenMP version
ENV QUIP_ROOT /opt/quip

# To build within the image without additonal libraries use
# the git+VANILLA version
# RUN git clone https://github.com/libAtoms/QUIP.git ${QUIP_ROOT}
# ENV BUILD NOGAP
ENV BUILD ALL
ADD . ${QUIP_ROOT}

# LAMMPS compilation
# lammps should be linked with SERIAL version of QUIP
# other configurations are untested and too complicated
# for a user
ENV QUIP_ARCH linux_x86_64_gfortran
ENV LAMMPS_PATH /opt/lammps

# build only libquip to keep a slim image. Makefile.inc required to
# compile lammps
RUN cd ${QUIP_ROOT} \
    && mkdir -p build/${QUIP_ARCH} \
    && cp docker/arch/${BUILD}_Makefile.${QUIP_ARCH}.inc build/${QUIP_ARCH}/Makefile.inc \
    && make libquip > /dev/null \
    && find build/${QUIP_ARCH} -type f ! \( -name '*.a' -o -name 'Makefile.inc' \) -delete

# TODO: prune any unwanted directories in this command
RUN mkdir -p ${LAMMPS_PATH} \
    && cd ${LAMMPS_PATH} \
    && curl http://lammps.sandia.gov/tars/lammps-stable.tar.gz | tar xz --strip-components 1

# Clean up Obj files immedaitely to keep image smaller
# use 2 make jobs to hopefully speed up travis
RUN cd ${LAMMPS_PATH}/src \
    && make yes-all \
    && make no-lib \
    && make yes-user-quip yes-python \
    && make -j 2 mpi \
    && make -j 2 mpi mode=shlib \
    && make install-python \
    && make clean-all

ENV PATH ${LAMMPS_PATH}/src/:${PATH}

# TODO: mpi quip

# QUIP for use
# TODO: install binaries

ENV QUIP_ARCH linux_x86_64_gfortran_openmp

RUN cd ${QUIP_ROOT} \
    && mkdir -p build/${QUIP_ARCH} \
    && cp docker/arch/${BUILD}_Makefile.${QUIP_ARCH}.inc build/${QUIP_ARCH}/Makefile.inc \
    && make > /dev/null \
    && make install-quippy > /dev/null

ENV PATH ${QUIP_ROOT}/build/${QUIP_ARCH}:${PATH}

# ENTRYPOINT ["/bin/bash", "-c"]

CMD jupyter notebook --port=8899 --ip='*' --allow-root --NotebookApp.token='' --NotebookApp.password=''

EXPOSE 8899
