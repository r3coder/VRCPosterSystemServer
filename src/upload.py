from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Please Follow Instructions on https://d35mpxyw7m7k7g.cloudfront.net/bigdata_1/Get+Authentication+for+Google+Service+API+.pdf to generate credentials.json
# If your credentials.json is not accessible from the server (i.e. no X server), you may need to copy code on desktop, and generate from there, and copy credentials.json back to the server


gauth = GoogleAuth()           
gauth.LoadCredentialsFile("credentials.json")
drive = GoogleDrive(gauth)  

upload_file_list = ['poster.mp4',]
for upload_file in upload_file_list:
	gfile = drive.CreateFile({'id': '1XDxCJiFcjcSCgpIQmRi22tWAFn17q_Bo'})
	# Read file and set it as the content of this instance.
	gfile.SetContentFile(upload_file)
	gfile.Upload() # Upload the file.


upload_file_list = ['calendar.mp4',]
for upload_file in upload_file_list:
	gfile = drive.CreateFile({'id': '1zSk-UdD9pv0Odsl4Q-19aP89kylcryIF'})
	# Read file and set it as the content of this instance.
	gfile.SetContentFile(upload_file)
	gfile.Upload() # Upload the file.

# file_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format('1cIMiqUDUNldxO6Nl-KVuS9SV-cWi9WLi')}).GetList()
# for file in file_list:
# 	print('title: %s, id: %s' % (file['title'], file['id']))

# for i, file in enumerate(sorted(file_list, key = lambda x: x['title']), start=1):
# 	print('Downloading {} file from GDrive ({}/{})'.format(file['title'], i, len(file_list)))
# 	file.GetContentFile(file['title'])