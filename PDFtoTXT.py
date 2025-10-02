import PyPDF2

def pdf_to_txt(pdf_path, txt_path):
    # Открываем PDF в режиме чтения двоичных данных
    with open(pdf_path, 'rb') as pdf_file:
        print(f'Открытие файла {pdf_path}...')
        reader = PyPDF2.PdfReader(pdf_file)
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            for page_num, page in enumerate(reader.pages, start=1):
                print(f'[ {round((page_num/len(reader.pages))*100, 2)}% | {page_num}/{len(reader.pages)} ]')
                text = page.extract_text()
                if text:
                    txt_file.write(f"\n\n--- Страница {page_num} ---\n")
                    txt_file.write(text)
                else:
                    txt_file.write(f"\n\n--- Страница {page_num} (нет текста, возможно это скан) ---\n")

if __name__ == "__main__":
    pdf_to_txt("input2.pdf", "output2.txt")

