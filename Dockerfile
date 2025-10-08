RUN apt-get update &&\
    apt-get install -y libgl1-mesa-dev && \
    apt-get install -y python3.11-dev && \
    apt-get install -y python3-pip && \
    apt-get install -y wget && \
    apt-get install -y build-essential &&  \
    apt-get install -y cmake && \
    apt-get install -y libgmp-dev &&  \
    apt-get install -y libreadline-dev &&  \
    apt-get install -y zlib1g-dev &&  \
    apt-get install -y libboost-program-options-dev && \
    apt-get install -y libboost-serialization-dev && \
    apt-get install -y libboost-regex-dev && \
    apt-get install -y libboost-iostreams-dev && \
    apt-get install -y libtbb-dev

RUN python3.11 -m pip install minizinc && \
    python3.11 -m pip install minizinc[dzn] && \
    python3.11 -m pip install z3-solver && \
    python3.11 -m pip install pulp && \
    python3.11 -m pip install matplotlib && \
    python3.11 -m pip install highspy && \
    python3.11 -m pip install ortools && \
    python3.11 -m pip install pyscipopt

ARG MINIZINC_VERSION=2.8.5

RUN wget https://github.com/MiniZinc/MiniZincIDE/releases/download/$MINIZINC_VERSION/MiniZincIDE-$MINIZINC_VERSION-bundle-linux-x86_64.tgz
RUN tar -xvf MiniZincIDE-$MINIZINC_VERSION-bundle-linux-x86_64.tgz
ENV PATH="${PATH}:/MiniZincIDE-$MINIZINC_VERSION-bundle-linux-x86_64/bin"

WORKDIR /cdmo

ADD . .

RUN chmod +x source/run_all.sh

CMD ["/bin/bash"]