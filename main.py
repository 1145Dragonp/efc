import subprocess
import sys
import os
import threading
import time

# 确保当前脚本所在目录在 Python 路径中，以便能够导入同级模块
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import execute_command, show_help
# 注意: 不再直接导入 start_server 等用于本地线程启动的函数，而是通过子进程管理
# 但 add_user 可能还需要? 不，add_user 是服务端内部逻辑。
# 如果 main.py 还要支持本地测试或其他，保留导入也没关系，但 @runserver 将改用子进程。
from server import add_user 
from client import start_client, connect_to_server, send_command_to_server

# 全局配置
SERVER_PORT = 8080
server_process = None
server_monitor_thread = None
is_server_running = False

def start_server_subprocess():
    """
    在子进程中启动服务端
    """
    global server_process, is_server_running
    if server_process and server_process.poll() is None:
        print("[警告] 服务端已经在运行中。")
        return

    print(f"[系统] 正在启动服务端子进程 (端口: {SERVER_PORT})...")
    try:
        # 使用当前 Python 解释器运行 server.py
        cmd = [sys.executable, os.path.join(script_dir, "server.py"), str(SERVER_PORT)]
        server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        is_server_running = True
        print(f"[系统] 服务端子进程已启动 (PID: {server_process.pid})")
        
        # 启动监视线程
        t = threading.Thread(target=monitor_server_process, daemon=True)
        t.start()
        
    except Exception as e:
        print(f"[错误] 启动服务端子进程失败: {e}")
        is_server_running = False

def monitor_server_process():
    """
    监视服务端进程，如果挂掉则自动重启
    """
    global server_process, is_server_running
    while True:
        if server_process:
            poll_result = server_process.poll()
            if poll_result is not None:
                # 进程已结束
                print(f"[监视器] 服务端进程已退出 (返回码: {poll_result})")
                is_server_running = False
                # 如果是预期内的关闭（比如手动停止），可以不重启。
                # 这里简单处理：只要不是手动停止标记，就尝试重启。
                # 由于没有复杂的状态机，我们假设只要 is_server_running 曾经为 True 且非手动停止，就重启。
                # 为了简化，我们引入一个 manual_stop 标志，或者在这里判断。
                # 简单策略：如果进程意外退出，等待2秒后重启。
                if not hasattr(monitor_server_process, 'manual_stop') or not monitor_server_process.manual_stop:
                    print("[监视器] 检测到服务端异常退出，将在 2 秒后尝试重启...")
                    time.sleep(2)
                    # 重新赋值 manual_stop 为 False 以防万一
                    if hasattr(monitor_server_process, 'manual_stop'):
                        monitor_server_process.manual_stop = False
                    start_server_subprocess()
                else:
                    print("[监视器] 服务端已手动停止，不再重启。")
                    break
        time.sleep(1)

def stop_server_subprocess():
    """
    停止服务端子进程
    """
    global server_process, is_server_running
    if server_process:
        print("[系统] 正在停止服务端...")
        # 设置监视器的标志，防止自动重启
        monitor_server_process.manual_stop = True
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        server_process = None
        is_server_running = False
        print("[系统] 服务端已停止。")
    else:
        print("[提示] 服务端未在运行。")

def main():
    print(">")
    print("输入 '@help' 查看帮助")
 
    
    current_mode = "local" # local, server, client

    while True:
        try:
            # 获取用户输入，使用 > 标志
            cmd = input("\n> ").strip()
            
            if not cmd:
                continue
                
            if cmd.lower() == '@stop':
                # 如果服务端在运行，先停止服务端
                if current_mode == "server" or is_server_running:
                    stop_server_subprocess()
                print("退出程序。")
                break
            
            # 检查是否为软件内部命令 (@开头)
            if cmd.startswith('@'):
                parts = cmd.split()
                sub_cmd = parts[0][1:].strip().lower()
                
                if sub_cmd == 'help':
                    show_help()
                elif sub_cmd == 'setport':
                    if len(parts) != 2:
                        print("[用法] @setport <端口号>")
                    else:
                        try:
                            new_port = int(parts[1])
                            if 1 <= new_port <= 65535:
                                global SERVER_PORT
                                SERVER_PORT = new_port
                                print(f"[配置] 服务端端口已修改为: {new_port}")
                            else:
                                print("[错误] 端口号必须在 1-65535 之间")
                        except ValueError:
                            print("[错误] 无效的端口号")
                elif sub_cmd == 'runserver':
                    current_mode = "server"
                    start_server_subprocess()
                    
                elif sub_cmd == 'runclient':
                    current_mode = "client"
                    msg = start_client()
                    print(msg)
                elif sub_cmd == 'newuser':
                    # 注意：由于服务端现在是独立进程，main.py 无法直接操作 server_users 内存
                    # 所以 @newuser 在本地模式下可能无法直接生效，除非通过 HTTP 请求添加用户
                    # 或者我们保留旧的直接调用方式，但这要求 server.py 暴露 API 或共享文件
                    # 鉴于 server.py 使用 JSON 文件，我们可以直接调用 add_user，它会写入文件
                    # 但服务端进程需要重新加载用户或者实时读取。
                    # 为了简单，我们假设服务端每次请求都读取最新文件，或者我们通知服务端重载。
                    # 这里保持调用 add_user，它会更新 user.json。
                    # 如果服务端缓存了用户，可能需要重启或增加重载命令。
                    # 修改 server.py 的 load_users 在每次请求时检查文件变更？或者简单起见，重启服务端。
                    # 这里暂且保持原样，用户可能需要重启服务端才能使新用户生效，或者我们在 server.py 中每次请求都 load_users (性能稍差但一致性好)。
                    # 建议在 server.py 的 do_GET 开始时调用 load_users() 以确保最新。
                    
                    if len(parts) != 3:
                        print("[用法] @newuser <用户名> <密码>")
                    else:
                        username = parts[1]
                        password = parts[2]
                        add_user(username, password)
                        print(f"[本地] 用户 '{username}' 已添加到 user.json。")
                        print("[提示] 如果服务端已启动，可能需要重启服务端或等待其重新加载用户配置。")
                        
                elif sub_cmd == 'intoservr':
                    if current_mode != "client":
                        print("[错误] 只有在客户端模式下才能配置连接。请先执行 @runclient")
                    else:
                        if len(parts) != 4:
                            print("[用法] @intoservr <IP地址> <用户名> <密码>")
                        else:
                            ip_input = parts[1]
                            username = parts[2]
                            password = parts[3]
                            connect_to_server(ip_input, username, password)
                
                elif sub_cmd == 'restart':
                    # 新增: 远程重启服务端
                    if current_mode == "client":
                        print("[客户端] 正在发送重启指令到服务端...")
                        send_command_to_server("__RESTART__")
                        print("[提示] 重启指令已发送。服务端将重启，连接可能会暂时中断。")
                    else:
                        print("[错误] 只有在客户端模式下才能使用 @restart 重启远程服务端。")
                        
                else:
                    print(f"[未知命令] 未知的软件命令: {cmd}。输入 @help 查看用法。")
                
                continue

            # 修改: 增加对非本地模式下普通输入的提示，避免用户以为程序无反应
            if current_mode != "local":
                # 如果是在客户端模式，且不是内部命令，则尝试发送给服务端
                if current_mode == "client":
                    send_command_to_server(cmd)
                else:
                    print(f"[提示] 当前处于 [{current_mode}] 模式。普通命令仅在 [local] 模式下执行。请使用 @ 开头的命令进行操作，或输入 @stop 退出。")
                continue

            # 简单的安全检查：禁止某些危险命令（示例）
            dangerous_commands = ['rm -rf /', 'format', 'del /s /q']
            if any(dc in cmd.lower() for dc in dangerous_commands):
                print("[安全警告] 检测到潜在危险命令，已拒绝执行。")
                continue

            print(f"正在执行: {cmd}")
            stdout, stderr, code = execute_command(cmd)
            
            if stdout:
                print(" ")
                print(stdout)
                
            if stderr:
                print("")
                print(stderr)
                
            print(f" {code}")
            
        except KeyboardInterrupt:
            print("\n\n用户中断，退出程序。")
            # 清理服务端进程
            if is_server_running:
                stop_server_subprocess()
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()