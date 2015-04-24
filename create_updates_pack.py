#!/usr/bin/env python
# coding: utf-8

''' Создает пакет обновлений проекта, определяя разницу между содержимым файлов и БД (на базе git) '''

# Script response (not in DEBUG mode):
# NULL (NOTHING!) if ALL OK. Overwise – logging error to file and NULL (NOTHING!) in output.

# Error codes description.
# 1: Argument of cmd <path-to-clan-site-build-folder> doesn't exists
# 2: Directory <path-to-clan-site-build-folder> doesn't exists
# 3: Last current version path doesn't exists
# 4: Notice: updates pack dir not exists in clansite build folder. EXIT.

import sys, os, ast, time, shutil, distutils.core, subprocess
import MySQLdb as mysql

DEBUG = True

# Params.
PATH_SCRIPT_PARSER	   			= '<removed>'
PATH_LOG_FILE					= '<removed>'

ENGINE_PATH 					= '<removed>'
ENGINE_FILE_CURRENT_VERSION		= 'current_version'
ENGINE_FILE_CURRENT_TITLE		= 'current_title'
ENGINE_FILE_CURRENT_DESCRIPTION	= 'current_description'
ENGINE_FILE_CURRENT_RELEASE_DT	= 'current_release_dt'

UPDATES_GIT_REPO_PATH			= '<removed>'

UPDATES_DIR 					= 'updates'
UPDATES_FILE_CURRENT_VERSION	= 'version'
UPDATES_FILE_TITLE				= 'title'
UPDATES_FILE_DESCRIPTION		= 'description'
UPDATES_FILE_RELEASE_DT			= 'release_dt'
UPDATES_DIR_MYSQL				= 'mysql'
UPDATES_DIR_FILES				= 'files'

UPDATES_PACK_DIR				= 'updates_pack'
UPDATES_PACK_DIR_MYSQL			= 'mysql'
UPDATES_PACK_FILE_VERSION		= 'version.upd'
UPDATES_PACK_FILE_TITLE	 		= 'title.upd'
UPDATES_PACK_FILE_DESCRIPTION	= 'description.upd'

CMD_GIT_REPO_PREPARE			= 'git reset HEAD . && git clean -f -d && git checkout master -f'
CMD_GIT_DIFF					= 'git diff HEAD HEAD~1 --name-only'
CMD_GIT_REPO_UPDATE_PATTERN		= 'git add -A && git commit -m "%s" && git push origin master'
CMD_SYMLINK_PATTERN				= 'cd %s && ln -snf %s %s'

TEXT_PATTERN_GIT_REPO_UPDATE	= 'Пакет обновлений #%s сформирован и выложен'

# Маппинг путей необходим для корректного формирования пакета обновлений, 
# который имеет свою структуру (files; mysql; current_version, title, description)
UPDATES_PATH_MAPPING			= {'default_site' : 'files'}
UPDATES_PATH_IGNORE				= [] #['updates_pack', 'default_site_db', '...']
UPDATES_PATH_PERMITTED			= ['default_site']



def parse( file_path, mode = 1 ):
	file_content = ast.literal_eval( os.popen( '%s %s %s' % ( PATH_SCRIPT_PARSER, file_path, mode )  ).read() )
	if 3 == file_content:
		return false
	return file_content if (2 == mode) else "\n".join(file_content)

# Logging function (in local log file).
def log( log_record = '' ):
	open( PATH_LOG_FILE, "a" ).write( log_record + "\r\n" )

def exitScript( error_num = 0 ):
		if (0 == error_num):
			sys.exit()

		log_record = time.strftime( "%Y-%m-%d %H:%M:%S ", time.gmtime() )

		if (1 == error_num):
			print 'USE PATTERN: ./create_updates_pack.py <path-to-clan-site-build-folder>'
			log_record += 'Error: argument <path-to-clan-site-build-folder> not exists'
		elif (2 == error_num):
			log_record += 'Error: directory <path-to-clan-site-build-folder> not exists'
		elif (3 == error_num):
			log_record += 'Error: last current engine version file doesnt exists'
		elif (4 == error_num):
			log_record += 'Notice: updates pack dir doesnt exists in clansite build folder. EXIT.'
		else:
			log_record += 'Undefined error'

		log( log_record )
		if DEBUG:
			print log_record
		sys.exit()



# //
# // ЭТАП 1: Создать новую директорию с обновлениями движка
# //

if (len(sys.argv) < 2):
	exitScript( 1 )

CLANSITE_BUILD_PATH = str(sys.argv[ 1 ])

if DEBUG:
	print 'site build path passed: ' + CLANSITE_BUILD_PATH


# – Проверить, есть ли в корне проекта папка "updates_pack" с информацией об обновлении
# 	– Если нет – завершаем работу

if not os.path.exists(CLANSITE_BUILD_PATH):
	if DEBUG:
		print 'Clansite build path does not exists'
	exitScript( 2 )

UPDATES_PACK_PATH = CLANSITE_BUILD_PATH + '/' + UPDATES_PACK_DIR

if not os.path.exists(UPDATES_PACK_PATH):
	if DEBUG:
		print 'updates_pack not found in clansite build path (' + UPDATES_PACK_PATH + ')'
	exitScript( 4 )


ENGINE_LAST_CURRENT_VERSION_PATH = ENGINE_PATH + '/' + ENGINE_FILE_CURRENT_VERSION

if DEBUG:
	print 'Engine last current version file path: ' + ENGINE_LAST_CURRENT_VERSION_PATH

if not os.path.exists(ENGINE_LAST_CURRENT_VERSION_PATH):
	if DEBUG:
		print 'last current version file does not exists'
	exitScript( 3 )


UPDATES_PACK_VERSION_PATH = UPDATES_PACK_PATH + '/' + UPDATES_PACK_FILE_VERSION

# – Если в папке нет файла current_version.upd
# 	– Определить новое значение current_version как [current_version + 1]
if not os.path.exists(UPDATES_PACK_VERSION_PATH):
	if DEBUG:
		print 'version file does not exists in updates pack'
	NEW_CURRENT_VERSION = int(parse(ENGINE_LAST_CURRENT_VERSION_PATH)) + 1


# – Если есть:
# 	– Определить новое значение current_version как указанная цифра в файле current_version.upd
else:
	if DEBUG:
		print 'hey! version file EXISTS in updates pack!'
	NEW_CURRENT_VERSION = parse(UPDATES_PACK_VERSION_PATH)


# – Зафиксировать путь к директории с новым пакетом обновлений
ENGINE_UPDATE_PACK_PATH = UPDATES_GIT_REPO_PATH + '/' + UPDATES_DIR + '/' + str(NEW_CURRENT_VERSION)

if DEBUG:
	print 'New engine update pack path: ' + ENGINE_UPDATE_PACK_PATH



# //
# // ЭТАП 2: Создание пакета обновлений в локальном репозитории
# //

git_prepare_cmd = "cd %s && %s" % (UPDATES_GIT_REPO_PATH, CMD_GIT_REPO_PREPARE)

# prepare repo
if DEBUG:
	print 'Executing command (updates-repo prepare) >>> ' + git_prepare_cmd
	
os.popen(git_prepare_cmd)


if os.path.exists(ENGINE_UPDATE_PACK_PATH):
	shutil.rmtree(ENGINE_UPDATE_PACK_PATH)

os.makedirs(ENGINE_UPDATE_PACK_PATH)
os.makedirs(ENGINE_UPDATE_PACK_PATH + '/' + UPDATES_DIR_MYSQL)
os.makedirs(ENGINE_UPDATE_PACK_PATH + '/' + UPDATES_DIR_FILES)

if DEBUG:
	print 'struct created: updates/' + str(NEW_CURRENT_VERSION) + '/[mysql,files]'


# – Проверить, присутствует ли папка "mysql" в пакете обновлений:
# 	– Если да: 
# 		– Скопировать все содержимое папки "mysql" из пакета обновлений в папку "mysql" с пакетом обновления для сервера

UPDATES_PACK_MYSQL_PATH = UPDATES_PACK_PATH + '/' + UPDATES_PACK_DIR_MYSQL

if os.path.exists(UPDATES_PACK_MYSQL_PATH) and os.path.isdir(UPDATES_PACK_MYSQL_PATH) and len(os.listdir(UPDATES_PACK_MYSQL_PATH)) > 0:
	if DEBUG:
		print 'mysql folder not empty in updates_pack. lets copy mysql folder content...'
	result = distutils.dir_util.copy_tree(UPDATES_PACK_MYSQL_PATH, ENGINE_UPDATE_PACK_PATH + '/' + UPDATES_DIR_MYSQL)
	if DEBUG:
		print 'copied:'
		print "\n".join(result)


# – Получить список файлов и директорий обновления (выполнение git diff HEAD HEAD~1 --name-only)
# 	– Если список файлов НЕ пуст:
# 		– Скопировать все файлы из списка в новый пакет обновлений, в созданную папку "files"

git_get_diff_cmd = "cd %s && %s" % (CLANSITE_BUILD_PATH, CMD_GIT_DIFF)

# get diff
if DEBUG:
	print 'Executing command (build-repo diff) >>> ' + git_get_diff_cmd
new_files = os.popen(git_get_diff_cmd).read().split("\n")

if DEBUG:
	print 'output (git diff): '
	print "\n".join(new_files) if new_files else '(null...)'

if len(new_files) > 0:
	for path in new_files:
		if not path:
			continue
		path_parts = path.split('/')
		try:
			permitted = False
			for index, part in enumerate(path_parts):
				if part in UPDATES_PATH_IGNORE:
					if DEBUG:
						print "Path: '" + path + "' will be ignored (script config)"
						raise PathIgnoredException()
				if part in UPDATES_PATH_PERMITTED:
					if DEBUG:
						print "Path: '" + path + "' exists in permitted list (script config)"
					permitted = True
				if part in UPDATES_PATH_MAPPING:
					path_parts[index] = UPDATES_PATH_MAPPING[part]
			if len(UPDATES_PATH_PERMITTED) > 0 and not permitted:
				if DEBUG:
					print "Permitted option enabled (permitted list not empty). Path not permitted (script config)"
				raise PathNotPermittedException()
		except:
			continue
		mapped_path = '/'.join(path_parts)
		if DEBUG:
			print "Get path: '" + path + "'. After mapping: '" + mapped_path + "'"
		path_src = CLANSITE_BUILD_PATH + '/' + path
		path_dst = ENGINE_UPDATE_PACK_PATH + '/' + mapped_path
		if not os.path.exists(path_src):
			if DEBUG:
				print "Can't copy path: '" + path_src + "': bad path (null/not exists)"
			continue
		try:
			if os.path.isdir(path_src):
				distutils.dir_util.copy_tree(path_src, path_dst)
			else:
				distutils.dir_util.mkpath(os.path.dirname(path_dst))
				shutil.copyfile(path_src, path_dst)
		except Exception, e:
			if DEBUG:
				print "Error received: " + str(e)
		else:
			if DEBUG:
				print "Success copy path: '" + path_src + "'"
else:
	if DEBUG:
		print 'No changes. <files> folder will be empty!'


# – Создать в новой папке с названием версии файл current_version, в который поместить цифру новой версии (сформированный ранее current_version)
# – Скопировать файлы description.upd и title.upd в новую папку с названием версии (под именами title и description, без расширения "upd")

f = open(ENGINE_UPDATE_PACK_PATH + '/' + UPDATES_FILE_CURRENT_VERSION, "w")
f.write(str(NEW_CURRENT_VERSION))
f.close()

f = open(ENGINE_UPDATE_PACK_PATH + '/' + UPDATES_FILE_TITLE, "w")
f.write(str(parse(UPDATES_PACK_PATH + '/' + UPDATES_PACK_FILE_TITLE)))
f.close()

f = open(ENGINE_UPDATE_PACK_PATH + '/' + UPDATES_FILE_DESCRIPTION, "w")
f.write(str(parse(UPDATES_PACK_PATH + '/' + UPDATES_PACK_FILE_DESCRIPTION)))
f.close()

f = open(ENGINE_UPDATE_PACK_PATH + '/' + UPDATES_FILE_RELEASE_DT, "w")
f.write(str(int(time.time())))
f.close()

if DEBUG:
	print 'Created updates_pack <version> file'
	print 'Created updates_pack <title> file'
	print 'Created updates_pack <description> file'
	print 'Created updates_pack <release_dt> file'


# – В корне проекта создать симлинки (относительные) на файлы current_version, title, description
# 	(указывают на эти файлы в новой папке с названием версии)

RELATIVE_UPDATES_PATH = './' + UPDATES_DIR + '/' + str(NEW_CURRENT_VERSION)

os.popen(CMD_SYMLINK_PATTERN % (UPDATES_GIT_REPO_PATH, RELATIVE_UPDATES_PATH + '/' + UPDATES_FILE_CURRENT_VERSION , './' + ENGINE_FILE_CURRENT_VERSION))
os.popen(CMD_SYMLINK_PATTERN % (UPDATES_GIT_REPO_PATH, RELATIVE_UPDATES_PATH + '/' + UPDATES_FILE_TITLE           , './' + ENGINE_FILE_CURRENT_TITLE))
os.popen(CMD_SYMLINK_PATTERN % (UPDATES_GIT_REPO_PATH, RELATIVE_UPDATES_PATH + '/' + UPDATES_FILE_DESCRIPTION     , './' + ENGINE_FILE_CURRENT_DESCRIPTION))
os.popen(CMD_SYMLINK_PATTERN % (UPDATES_GIT_REPO_PATH, RELATIVE_UPDATES_PATH + '/' + UPDATES_FILE_RELEASE_DT      , './' + ENGINE_FILE_CURRENT_RELEASE_DT))

if DEBUG:
	print 'Symlinks created: current_version, current_title, current_description, current_release_dt'



# //
# // ЭТАП 3 (ФИНАЛ): Коммит изменений в проекте
# //

# – Коммит изменений проекта с текстом "Пакет обновлений #x сформирован и выложен"
# 	(+ push в master-ветку С ХУКОМ на последующий автодеплой)

git_repo_update_commit_text = TEXT_PATTERN_GIT_REPO_UPDATE % NEW_CURRENT_VERSION
git_repo_update_cmd_with_commit_text = CMD_GIT_REPO_UPDATE_PATTERN % git_repo_update_commit_text
git_repo_update_cmd = "cd %s && %s" % (UPDATES_GIT_REPO_PATH, git_repo_update_cmd_with_commit_text)

# update repo
if DEBUG:
	print 'Executing command (repo update: add->commit->push) >>> ' + git_repo_update_cmd

git_repo_udpate_cmd_result = subprocess.Popen(git_repo_update_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

if DEBUG:
	print 'STDOUT (repo updating):'
	print git_repo_udpate_cmd_result.stdout.read()
	print 'STDERR (repo updating):'
	print git_repo_udpate_cmd_result.stderr.read()



exitScript(0)



