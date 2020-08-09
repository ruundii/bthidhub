# Copyright (c) 2020 ruundii. All rights reserved.

import crypt,  spwd, subprocess

def is_valid_current_password(user, current_password):
    password = spwd.getspnam(user).sp_pwdp
    return crypt.crypt(current_password, password)==password

def set_new_password(user, new_password):
    p = subprocess.Popen([ "/usr/sbin/chpasswd" ], universal_newlines=True, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate(user + ":" + new_password + "\n")
    assert p.wait() == 0
    return not (stdout or stderr)