# EPFL Extended Depth of Field (reference implementation)

## What and why

The ImageJ plugin of the Biomedical Imaging Group, EPFL, is the published implementation of complex-wavelet
extended depth of field (Forster, Van De Ville, Berent, Sage and Unser 2004, *Microscopy Research and Technique*
65:33-42, doi:[10.1002/jemt.20092](https://doi.org/10.1002/jemt.20092)). Laminario does not run it: its engine
(`app/imaging/edf.py`, `app/imaging/complex_wavelet.py`) is a port, and the plugin is the independent oracle the
port is measured against.

## Install (exact, verified)

Source and binaries from
[Biomedical-Imaging-Group/EDF-Extended-Depth-of-Field](https://github.com/Biomedical-Imaging-Group/EDF-Extended-Depth-of-Field)
(`dist/Extended_Depth_Field.jar`, `lib/ij.jar`), run unmodified with Java 17 or later through two headless
runners, `RunEdf.java` (the "high" and "low-medium" presets) and `WaveletCheck.java` (the transform alone). Jars,
runners, sample stacks and outputs live in the local data vault (`edf-reference/`), never in git.

## Usage

```bash
javac -cp "bin/Extended_Depth_Field.jar;bin/ij.jar" -d build RunEdf.java WaveletCheck.java
java -cp "bin/Extended_Depth_Field.jar;bin/ij.jar;build" RunEdf dome/stack.tif dome high
```

## Applying it here

- The port equals the plugin on 100 percent of height-map pixels on its three sample stacks, both methods (R-204),
  and the transform equals `ComplexWavelet` within 3e-13 (the transform gate).
- The composite gate compares against the plugin on the square-padded reference (R-016).

## Caveats and licence

- The plugin's consistency checks take the image height as the x extent; on non-square padded sizes they visit
  regions that are not the sub-bands. On stacks with known focus that is three times less often right; Laminario
  uses the true geometry and keeps the plugin's convention as an option for the proof (F-014).
- The plugin's sources use bare carriage-return line endings.
- GPL-3.0; run unmodified to produce reference data; no code is copied into Laminario.
