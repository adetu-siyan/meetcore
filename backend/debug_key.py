from dotenv import load_dotenv
load_dotenv()
import os

key = os.getenv('ASSEMBLYAI_API_KEY')
if key is None:
    print("KEY IS NONE - not loading at all")
else:
    print(f"Length: {len(key)}")
    print(f"First 6 chars: {key[:6]}")
    print(f"Last 4 chars: {key[-4:]}")
    print(f"Has spaces: {' ' in key}")
    print(f"Has newline: {chr(10) in key}")
    print(f"Starts with quote: {key[0] in [chr(34), chr(39)]}")
    print(f"Raw repr: {repr(key[:10])}")