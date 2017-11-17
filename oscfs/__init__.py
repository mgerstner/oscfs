try:
	# TODO: make a sanity check whether the this is really fusepy and not
	# python-fuse
	import fuse
except ImportError:
	print("Failed to import the python fuse module.")
	sys.exit(1)

try:
	import osc
except ImportError:
	print("Failed to import the python osc module.")
	sys.exit(1)

