import os
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging

# Configuração do logging para depuração
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Função de validação de CPF
def validar_cpf(cpf):
    logging.debug(f'Validando CPF: {cpf}')
    cpf = [int(digit) for digit in cpf]
    if len(cpf) != 11 or len(set(cpf)) == 1:
        logging.debug('CPF inválido: tamanho incorreto ou todos os dígitos iguais')
        return False

    for i in range(9, 11):
        val = sum((cpf[num] * ((i + 1) - num) for num in range(0, i)))
        dig = ((val * 10) % 11) % 10
        if dig != cpf[i]:
            logging.debug(f'CPF inválido: dígito verificador não corresponde - posição {i}')
            return False
    logging.debug('CPF válido')
    return True

# Função para varrer um arquivo em busca de CPFs
def search_file(file_path):
    results = []
    valid_cpfs = set()  # Usar conjunto para evitar duplicatas
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        except:
            logging.error(f'Não foi possível ler o arquivo: {file_path} - Arquivo não é de texto ou codificação desconhecida')
            return results, valid_cpfs

    # Procurar por CPFs no formato com pontuação e sem pontuação
    cpf_list = re.findall(r'\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}', content)
    for cpf in cpf_list:
        is_valid = validar_cpf(cpf.replace('.', '').replace('-', ''))
        status = "válido" if is_valid else "inválido"
        results.append(f'Arquivo: {file_path} - CPF encontrado: {cpf} - {status}\n')
        if is_valid:
            valid_cpfs.add(cpf)  # Adicionar CPF ao conjunto se for válido
    
    return results, valid_cpfs

# Função para varrer um diretório em busca de arquivos com CPFs
def search_files(directory):
    result_text.delete(1.0, tk.END)  # Limpar a área de texto de resultados
    logging.info(f'Iniciando busca no diretório: {directory}')

    files_to_search = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path) and os.path.getsize(file_path) < 50 * 1024 * 1024:  # Limite de 50 MB
                files_to_search.append(file_path)

    total_files = len(files_to_search)
    progress_bar["maximum"] = total_files
    total_valid_cpfs = set()  # Usar conjunto para evitar duplicatas
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(search_file, file): file for file in files_to_search}
        for i, future in enumerate(as_completed(futures)):
            try:
                file_path = futures[future]
                current_file_label.config(text=f'Processando: {file_path}')
                results, valid_cpfs = future.result()
                for result in results:
                    result_text.insert(tk.END, result)
                total_valid_cpfs.update(valid_cpfs)  # Atualizar conjunto com CPFs válidos
            except Exception as exc:
                logging.error(f'Ocorreu um erro ao processar o arquivo {futures[future]}: {exc}')
            result_text.insert(tk.END, '\n')
            progress_bar["value"] = i + 1

    result_text.insert(tk.END, f'Total de CPFs válidos encontrados: {len(total_valid_cpfs)}\n')
    result_text.insert(tk.END, 'CPFs válidos:\n')
    for cpf in total_valid_cpfs:
        result_text.insert(tk.END, f'{cpf}\n')
    current_file_label.config(text='Busca concluída!')

def browse_directory():
    directory = filedialog.askdirectory()
    if directory:
        directory_entry.delete(0, tk.END)
        directory_entry.insert(0, directory)

def start_search():
    directory = directory_entry.get()
    if os.path.isdir(directory):
        search_thread = threading.Thread(target=search_files, args=(directory,))
        search_thread.start()
    else:
        messagebox.showerror("Erro", "Por favor, selecione um diretório válido.")
        logging.error("Diretório inválido selecionado")

# Configuração da interface gráfica
root = tk.Tk()
root.title("Busca de CPFs em Arquivos")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

directory_label = tk.Label(frame, text="Diretório:")
directory_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

directory_entry = tk.Entry(frame, width=50)
directory_entry.grid(row=0, column=1, padx=5, pady=5)

browse_button = tk.Button(frame, text="Procurar", command=browse_directory)
browse_button.grid(row=0, column=2, padx=5, pady=5)

search_button = tk.Button(frame, text="Iniciar Busca", command=start_search)
search_button.grid(row=1, column=0, columnspan=3, pady=10)

progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(padx=10, pady=5)

current_file_label = tk.Label(root, text="")
current_file_label.pack(padx=10, pady=5)

result_text = scrolledtext.ScrolledText(root, width=80, height=20)
result_text.pack(padx=10, pady=10)

root.mainloop()
