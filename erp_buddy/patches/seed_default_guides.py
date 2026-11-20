from erp_buddy.setup.install import seed_default_guides


def execute():
	"""Guides used to be Markdown files in the app; sites that predate the DocType get them as records."""
	seed_default_guides()
