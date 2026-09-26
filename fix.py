file_path = 'frontend/src/pages/NioScreen.jsx'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

body_lines = lines[126:338]

with open('frontend/src/components/FluidSphere.jsx', 'w', encoding='utf-8') as f:
    f.write("import { useEffect } from 'react'\nimport * as THREE from 'three'\n\n")
    f.write("export function FluidSphere({ canvasRef, amplitudeRef, sloshRef, dark }) {\n")
    f.writelines(body_lines[1:]) # skip the `) {` line

new_lines = lines[:126] + lines[338:]
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
