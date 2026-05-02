import subprocess

def execute_command(command: str) -> tuple:
    """
    在本地系统中执行给定的命令。
    
    :param command: 要执行的字符串命令
    :return: (stdout, stderr, return_code)
    """
    try:
        # 使用 subprocess.run 执行命令
        # shell=True 允许执行复杂的 shell 命令，但在生产环境中需谨慎使用以防止注入攻击
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10  # 设置超时时间，防止命令挂起
        )
        
        # 解码输出，尝试处理不同编码
        try:
            stdout = result.stdout.decode('utf-8')
        except UnicodeDecodeError:
            stdout = result.stdout.decode('gbk', errors='ignore')
            
        try:
            stderr = result.stderr.decode('utf-8')
        except UnicodeDecodeError:
            stderr = result.stderr.decode('gbk', errors='ignore')
            
        return stdout, stderr, result.returncode
        
    except subprocess.TimeoutExpired:
        return "", "Command timed out", -1
    except Exception as e:
        return "", str(e), -1

def show_help():
    """
    显示帮助信息
    """
    help_text = """
=== 软件命令帮助 ===
@help       : 显示此帮助信息
@setport <端口> : 设置服务端端口 (默认 8080)
@runserver  : 开启服务端模式
@runclient  : 启动客户端模式
@newuser <用户> <密码> : (服务端) 创建新用户
@intoservr <ip> <用户> <密码> : (客户端) 配置服务器连接并发送心跳
其他输入    : 作为本地系统命令执行
    """
    print(help_text)
