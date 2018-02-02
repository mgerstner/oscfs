from __future__ import with_statement, print_function
import sys

try:
	import fuse
	# make sure we don't have the python-fuse module which uses a similar
	# but incompatible API
	# python-fuse has the APIVersion attribute which fusepy doesn't have.
	api_version = getattr(fuse, "APIVersion", None)
	if api_version != None:
		print("Wrong python fuse module is installed", file = sys.stderr)
		print("oscfs requires the fusepy module, this is the python-fuse module", file = sys.stderr)
		sys.exit(1)

except ImportError:
	print("Failed to import the python fuse module.", file = sys.stderr)
	sys.exit(1)

try:
	import osc
except ImportError:
	print("Failed to import the python osc module.", file = sys.stderr)
	sys.exit(1)

