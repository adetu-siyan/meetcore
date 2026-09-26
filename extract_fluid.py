import os
import re

file_path = r'frontend/src/pages/NioScreen.jsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find('function FluidSphere({')
if start_idx == -1:
    print("FluidSphere not found")
    exit(1)

brace_count = 0
end_idx = -1
in_func = False
for i in range(start_idx, len(content)):
    if content[i] == '{':
        brace_count += 1
        in_func = True
    elif content[i] == '}':
        brace_count -= 1
        if in_func and brace_count == 0:
            end_idx = i + 1
            break

fluid_sphere_code = "import { useEffect } from 'react'\nimport * as THREE from 'three'\n\nexport " + content[start_idx:end_idx]

with open(r'frontend/src/components/FluidSphere.jsx', 'w', encoding='utf-8') as f:
    f.write(fluid_sphere_code)

new_content = content[:start_idx] + content[end_idx:]

import_stmt = "import { FluidSphere } from '../components/FluidSphere'\n"
last_import = new_content.rfind('import ')
last_import_end = new_content.find('\n', last_import) + 1
new_content = new_content[:last_import_end] + import_stmt + new_content[last_import_end:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("FluidSphere extracted!")
