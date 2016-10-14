import json
import requests
import time
from urlparse import urlparse
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-t', action='store', dest='token', help='Enter API token')
parser.add_argument('-k', action='store', dest='key', help='Enter API key')
parser.add_argument('-T', action='store', dest='tagName', help='Enter your "tag name" (TAG MUST PRE-EXIST IN INVENTORY)')
parser.add_argument('-W', action='store_true', default=False, dest='writeTags', help='Commit to writing tags - otherwise just print results')
args = parser.parse_args()
token = args.token
key = args.key
tagName = args.tagName

maxResults = 500
offset = 0
pages = 0
tagWrite = 0

# Do a single result search to get the total results number to allow us to calculate how many pages we need. Sucks but works.
pageSearchParams = {'filters': [{'filters': [{'field': 'type','type': 'EQ','value': 'WEB_SITE'}]},{'filters': [{'field': 'responseCode','type': 'EQ','value': '301'},{'field': 'responseCode','type': 'EQ','value': '302'}]},{'filters': [{'field': 'inventoryState','type': 'EQ','value': 'CONFIRMED'}]}]}
pageSearch = requests.post('https://ws.riskiq.net/v1/inventory/search?results=1&offset=0', json=pageSearchParams, auth=(token, key))
getPages = pageSearch.json()
maxPages = (getPages['totalResults'] / maxResults)+1

while pages < maxPages:
	# Search for all confirmed website assets with 301 and 302 response codes.
	s = requests.Session()
	headers = {'results': maxResults, 'offset': offset}
	searchParams = {'filters': [{'filters': [{'field': 'type','type': 'EQ','value': 'WEB_SITE'}]},{'filters': [{'field': 'responseCode','type': 'EQ','value': '301'},{'field': 'responseCode','type': 'EQ','value': '302'}]},{'filters': [{'field': 'inventoryState','type': 'EQ','value': 'CONFIRMED'}]}]}
	response = s.post('https://ws.riskiq.net/v1/inventory/search?', params=headers, json=searchParams, auth=(token, key))
	searchResult = response.json()

	# Loop through the results pulling what we need - and construct the final 'name' out of the finalUrl.
	for i in searchResult['inventoryAsset']:
		try:
			assetID = i['assetID']
			initialUrl = i['webSite']['initialUrl']
			finalUrl = i['webSite']['finalUrl']
			initialASN = i['asn']['asnID']
			initialHost = i['host']['host']
			existingTags = i['tags']
			nameExtract = urlparse(finalUrl)
			finalName = nameExtract.scheme + '://' + nameExtract.netloc
			print initialUrl
			print finalName
			
			# Put the final 'name' in a search and extract the ASN number.
			finalSearchParams = {'filters': [{'filters': [{'field': 'type','type': 'IN','value': 'WEB_SITE'}]},{'filters': [{'field': 'name','type': 'EQ','value': finalName}]}]}
			finalAsnLookup = s.post('https://ws.riskiq.net/v1/inventory/search', json=finalSearchParams, auth=(token, key))
			finalAsnLoop = finalAsnLookup.json()
		
			for n in finalAsnLoop['inventoryAsset']:
				try:
					finalASN = n['asn']['asnID']
				except KeyError:
					break
			
			# Compare Initial and Final ASN - tag the Initial Url Website (AssetID) for non-matches.
			if initialASN != finalASN and args.writeTags == True:
				existingTags.extend([tagName])
				writeParams = {'ids':[assetID], 'tags':existingTags}
				write = s.post('https://ws.riskiq.net/v1/inventory/update', json=writeParams, auth=(token, key))
				tagWrite +=1
				print initialUrl,":",finalUrl,":",initialASN,":",finalASN
				print 'HTTP Response:', write.status_code # debug
				print write.text # debug
			elif initialASN != finalASN and args.writeTags == False:
				print initialUrl,":",finalUrl,":",initialASN,":",finalASN
				tagWrite +=1

		except KeyError:
			continue

	pages = pages+1
	offset = offset+500

print "Found", tagWrite, "ASN redirects."


