#!/usr/bin/env python

"""
Copies a remote in a local git repo, for the purpose of snapshotting its commit IDs
and preventing them from being garbage-collected.
"""

__version__ = '0.1'

import subprocess
import argparse


def split_lines(s):
	return s.rstrip("\r\n").replace("\r\n", "\n").split("\n")


def get_remotes(git_exe):
	return split_lines(subprocess.check_output([git_exe, "remote"]))


def get_refs(git_exe, remote):
	lines = split_lines(subprocess.check_output(["git", "for-each-ref", "refs/remotes/" + remote]))
	for line in lines:
		try:
			commit, rest = line.split(" ", 1)
			_, refname = rest.split("\t")
		except ValueError:
			print repr(line)
			raise
		assert _ == "commit", "Expected %r, was %r" % ("commit", _)
		yield (commit, refname)


def update_server_info(git_exe):
	subprocess.check_call(["git", "update-server-info"])


def get_src_section_lines(src_section):
	with open(".git/config", "rb") as f:
		captured_lines = []
		for line in f:
			if captured_lines:
				if line.startswith('['):
					# This line is already the next section, so we're done
					return captured_lines
				else:
					captured_lines.append(line)
			if line.rstrip("\r\n ") == '[%s]' % (src_section,):
				captured_lines.append(line)
	return captured_lines


def copy_git_config_section(src_section, dest_section):
	with open(".git/config", "ab") as f:
		lines = get_src_section_lines(src_section)
		new_lines = lines[:]
		new_lines[0] = lines[0].replace('[%s]' % (src_section,), '[%s]' % (dest_section,), 1)
		for line in new_lines:
			f.write(line)


class DestinationAlreadyExists(Exception):
	pass


class SourceDoesNotExist(Exception):
	pass


def main():
	parser = argparse.ArgumentParser(
		description="""
	Copies a remote in a local git repo, for the purpose of snapshotting its commit IDs
	and preventing them from being garbage-collected.
	""")

	parser.add_argument('-g', '--git', dest='git_exe', default='git',
		help="path to git executable, default 'git'")

	parser.add_argument('src_remote')
	parser.add_argument('dest_remote')

	args = parser.parse_args()
	git_exe = args.git_exe

	remotes = get_remotes(git_exe)

	if not args.src_remote in remotes:
		raise SourceDoesNotExist("Source remote %r doesn't exist" % (args.src_remote,))

	if args.dest_remote in remotes:
		raise DestinationAlreadyExists("Destination remote %r already exists" % (args.dest_remote,))

	copy_git_config_section('remote "%s"' % (args.src_remote,), 'remote "%s"' % (args.dest_remote,))

	pairs = list(get_refs(git_exe, args.src_remote))
	with open(".git/packed-refs", "ab") as f:
		for commit, refname in pairs:
			new_refname = refname.replace(
				"refs/remotes/%s/" % (args.src_remote,),
				"refs/remotes/%s/" % (args.dest_remote,),
				1)
			f.write("%s %s\n" % (commit, new_refname))

	update_server_info(git_exe)


if __name__ == '__main__':
	main()
