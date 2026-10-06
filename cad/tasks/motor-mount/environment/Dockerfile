# Text-to-CAD agent image: FreeCAD only, with no grader, validator, structured
# spec, or reference geometry. Held-back assets live only in the separate
# verifier image built from tests/Dockerfile.
FROM condaforge/miniforge3@sha256:7de9956cd783d48955835e61b8d212c26b2df901d5a5be8217bd58fb6c1bd5a4

RUN mamba install -n base -y -c conda-forge \
        python=3.12 "freecad=1.1.0" "numpy=2.4.6" scipy pydantic \
 && mamba clean -afy

RUN echo /opt/conda/lib > "$(python -c 'import site; print(site.getsitepackages()[0])')/freecad.pth" \
 && python -c "import FreeCAD, numpy, pydantic, scipy; assert FreeCAD.Version()[:3] == ['1', '1', '0'], FreeCAD.Version(); assert numpy.__version__ == '2.4.6', numpy.__version__; print('runtime ok: FreeCAD', '.'.join(FreeCAD.Version()[:3]), 'numpy', numpy.__version__)" \
 && freecadcmd --version \
 && ! command -v ccx

RUN userdel -r ubuntu 2>/dev/null || true

WORKDIR /app
COPY LICENSES/ /app/LICENSES/

ENV FREECAD_LIB=/opt/conda/lib:/opt/conda/Mod:/opt/conda/share/Mod

RUN mamba install -y -n base -c conda-forge --freeze-installed \
        nodejs \
        git \
 && mamba clean --all --yes

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        curl ca-certificates bash \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN printf 'export PATH=/opt/conda/bin:$PATH\n' > /etc/profile.d/01-conda-path.sh \
 && chmod 644 /etc/profile.d/01-conda-path.sh \
 && ln -sf /opt/conda/bin/freecadcmd /usr/local/bin/freecadcmd \
 && ln -sf /opt/conda/bin/python3    /usr/local/bin/python3 \
 && ln -sf /opt/conda/bin/python     /usr/local/bin/python
