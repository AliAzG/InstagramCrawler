import instagramcrawler
import os

IDs = open('./followers.txt')
results = IDs.read().splitlines()

for i in range(len(results)):
    os.system("python3 instagramcrawler.py -q '" + results[i] + "' -t 'profile_img' -n 200 -a auth.jason")