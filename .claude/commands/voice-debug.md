Debug the Discord voice pipeline.

Steps:
1. Check py-cord version:
   docker exec os-discord python3 -c "import discord; print(discord.__version__)"

2. Check Groq key configured:
   grep GROQ_API_KEY /opt/OS/services/.env | cut -c1-20

3. Test Groq transcription:
   docker exec os-discord python3 -c "
import os, sys
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/services/.env')
from groq import Groq
client = Groq(api_key=os.getenv('GROQ_API_KEY'))
print('Groq: OK')
"

4. Check voice logs:
   docker logs os-discord --tail 20 | grep -i voice

Report what's working and what's broken.
