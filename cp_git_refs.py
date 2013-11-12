#!/usr/bin/env python

"""
Snapshots a set of refs in a local git repo.  This lets you jump back in time
when commits are force-pushed, or when the remote's refs are otherwise
modified or deleted.
"""

__version__ = '0.5'

import os
import datetime
import subprocess
import argparse


def split_lines(s):
	x = s.rstrip("\r\n").replace("\r\n", "\n")
	return x.split("\n") if x else []


def get_refs(git_exe, base=None):
	args = ["git", "for-each-ref"]
	if base is not None:
		args += [base]
	lines = split_lines(subprocess.check_output(args))
	for line in lines:
		try:
			commit, rest = line.split(" ", 1)
			_, refname = rest.split("\t")
		except ValueError:
			print repr(line)
			raise
		# Also "tag"
		#assert _ == "commit", "Expected %r, was %r" % ("commit", _)
		yield (commit, refname)


def update_server_info(git_exe):
	subprocess.check_call(["git", "update-server-info"])


def is_bare_repo(): # (or cwd is in the .git/ of a non-bare repo)
	return os.path.isfile("HEAD") and os.path.isfile("config") and \
		os.path.isfile("packed-refs") and os.path.isdir("objects")


def get_git_filename(name):
	if is_bare_repo():
		return name
	return ".git/" + name


class RefAlreadyExists(Exception):
	pass


class MissingGitFile(Exception):
	pass


def get_expanded_base(format_string, t):
	return format_string.format(
		YMDHMS=t.strftime('%Y-%m-%d_%H-%M-%S')
	)


def copy_git_remote(git_exe, src_base, dest_base):
	t = datetime.datetime.now()
	dest_base_expanded = get_expanded_base(dest_base, t)

	pairs = list(get_refs(git_exe))
	existing_refs = set(x[1] for x in pairs)
	if not os.path.isfile(get_git_filename("packed-refs")):
		raise MissingGitFile("No packed-refs file; is this a git repo?")

	lines = []
	for commit, refname in pairs:
		if not refname.startswith(src_base + "/"):
			continue
		new_refname = refname.replace(src_base, dest_base_expanded, 1)
		assert new_refname != refname, new_refname
		if new_refname in existing_refs:
			raise RefAlreadyExists(new_refname)
		lines.append("%s %s\n" % (commit, new_refname))

	with open(get_git_filename("packed-refs"), "ab") as f:
		f.write("".join(lines))

	update_server_info(git_exe)


def main():
	parser = argparse.ArgumentParser(
		description="""
	Snapshots a set of refs in a local git repo.  This lets you jump back in time
	when commits are force-pushed, or when the remote's refs are otherwise
	modified or deleted.
	""")

	parser.add_argument('-g', '--git', dest='git_exe', default='git',
		help="path to git executable, default 'git'")

	parser.add_argument('src_base', help="The source base name (e.g. 'refs/remotes/origin' or 'refs/current').")
	parser.add_argument('dest_base', help="""The destination base name (e.g.
		'refs/snapshots/origin-2013-01-01' or 'refs/snapshot-2013-01-01').  Use
		{YMDHMS} for a timestamp.""")

	args = parser.parse_args()
	copy_git_remote(args.git_exe, args.src_base, args.dest_base)


if __name__ == '__main__':
	main()
