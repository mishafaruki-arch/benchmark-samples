# Verifier image (separate from the agent): FreeCAD + the freecad validator,
# with the held-back reference.FCStd baked at /opt/grader and the scorer/driver
# at /tests. Never shipped to the agent.
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

ARG FREECAD_VALIDATOR_VERSION=0.4.0
RUN python -m pip install --no-cache-dir \
        "gnucleus-freecad-validator==${FREECAD_VALIDATOR_VERSION}" \
 && python -c "from importlib.metadata import version; import FreeCAD, freecad_validator; validator_version = version('gnucleus-freecad-validator'); assert FreeCAD.Version()[:3] == ['1', '1', '0'], FreeCAD.Version(); assert validator_version == '${FREECAD_VALIDATOR_VERSION}', validator_version; print('verifier runtime ok:', FreeCAD.Version()[:3], validator_version)"

COPY grader/ /opt/grader/
COPY . /tests/
