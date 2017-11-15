try:
	import fuse
except ImportError:
	print("Failed to import the python fuse module.")
	sys.exit(1)

# this is a necessary declaration to export the correct API from python-fuse
fuse.fuse_python_api = (0, 2)

try:
	import osc
except ImportError:
	print("Failed to import the python osc module.")
	sys.exit(1)

