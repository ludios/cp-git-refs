#!/usr/bin/env python

"""
Copies a remote in a local git repo, for the purpose of snapshotting its commit IDs
and preventing them from being garbage-collected.
"""

__version__ = '0.2'

import datetime
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
	lines = get_src_section_lines(src_section)
	new_lines = lines[:]
	new_lines[0] = lines[0].replace('[%s]' % (src_section,), '[%s]' % (dest_section,), 1)
	with open(".git/config", "ab") as f:
		for line in new_lines:
			f.write(line)


class DestinationAlreadyExists(Exception):
	pass


class SourceDoesNotExist(Exception):
	pass


# Based on tagmyrebase.py:get_expanded_name
def get_expanded_remote(format_string, t, remotes):
	ymdn = None
	if '{YMDN}' in format_string:
		ymd = t.strftime('%Y-%m-%d')
		for n in xrange(1, 100000):
			proposed_ymdn = ymd + '.' + str(n)
			proposed_remote = get_expanded_remote(
				format_string.format(
					YMDN=proposed_ymdn,
					YMDHMS='{YMDHMS}'
				), t, remotes)
			if not proposed_remote in remotes:
				ymdn = proposed_ymdn
				break
		else:
			raise RuntimeError("100,000 remotes in one day is too many remotes")

	return format_string.format(
		YMDN=ymdn,
		YMDHMS=t.strftime('%Y-%m-%d_%H-%M-%S')
	)


def main():
	parser = argparse.ArgumentParser(
		description="""
	Copies a remote in a local git repo, for the purpose of snapshotting its commit IDs
	and preventing them from being garbage-collected.
	""")

	parser.add_argument('-g', '--git', dest='git_exe', default='git',
		help="path to git executable, default 'git'")

	parser.add_argument('src_remote', help="The source remote name.")
	parser.add_argument('dest_remote', help="""
		The destination remote name.  You can include {YMDN} or {YMDHMS} for a
		timestamp.""")

	args = parser.parse_args()
	t = datetime.datetime.now()
	git_exe = args.git_exe
	remotes = get_remotes(git_exe)
	src_remote = args.src_remote
	dest_remote_expanded = get_expanded_remote(args.dest_remote, t, remotes)

	if not args.src_remote in remotes:
		raise SourceDoesNotExist("Source remote %r doesn't exist" % (src_remote,))

	if dest_remote_expanded in remotes:
		raise DestinationAlreadyExists("Destination remote %r already exists" % (dest_remote_expanded,))

	copy_git_config_section('remote "%s"' % (src_remote,), 'remote "%s"' % (dest_remote_expanded,))

	pairs = list(get_refs(git_exe, src_remote))
	with open(".git/packed-refs", "ab") as f:
		for commit, refname in pairs:
			new_refname = refname.replace(
				"refs/remotes/%s/" % (src_remote,),
				"refs/remotes/%s/" % (dest_remote_expanded,),
				1)
			f.write("%s %s\n" % (commit, new_refname))

	update_server_info(git_exe)


if __name__ == '__main__':
	main()
