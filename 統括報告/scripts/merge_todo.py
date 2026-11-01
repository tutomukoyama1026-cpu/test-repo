#!/usr/bin/env python3
"""朝の報告に Todo（統括報告/Todo.html の項目）を差し込む。
使い方: python3 統括報告/scripts/merge_todo.py 統括報告/YYMMDD_朝の報告.html [統括報告/Todo.html]
・Todo の項目・期日は Todo.html を正本として社長が直す（項目の追加・削除・完了はここで）。
・差し込み位置は「緊急で対応すべき項目」の直後。すでに差し込み済みなら入れ替える。
・チェック状態は端末のブラウザに保存（キー sugiyama-todo-261031）。
"""
import re, sys
rep_p = sys.argv[1]
todo_p = sys.argv[2] if len(sys.argv) > 2 else '統括報告/Todo.html'
rep = open(rep_p, encoding='utf-8').read()
todo = open(todo_p, encoding='utf-8').read()

css = re.search(r'<style>(.*?)</style>', todo, re.S).group(1)
# :root の変数のうち Todo 専用の色だけ取り出す
vars_ = '#todo{--crit:#c62828;--crit-bg:#fdecec;--warn:#b26a00;--warn-bg:#fff4e0;--info:#1f5fa8;--info-bg:#e8f0fb}\n' \
        '@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) #todo{--crit:#ff7a7a;--crit-bg:#3a1d20;--warn:#ffb74d;--warn-bg:#36290f;--info:#8fb4e6;--info-bg:#18283c}}\n' \
        ':root[data-theme="dark"] #todo{--crit:#ff7a7a;--crit-bg:#3a1d20;--warn:#ffb74d;--warn-bg:#36290f;--info:#8fb4e6;--info-bg:#18283c}\n'
keep = []
for rule in re.findall(r'([^{}]+)\{([^{}]*)\}', re.sub(r'@media[^{]*\{([^{}]*\{[^{}]*\})*[^{}]*\}', '', css)):
    sel, body = rule[0].strip(), rule[1]
    if sel.startswith(':root') or sel in ('*', 'body', 'header', '.wrap', 'h1', 'header p', 'main', 'section'):
        continue
    sel = ','.join('#todo ' + s.strip() for s in sel.split(','))
    keep.append(f'{sel}{{{body}}}')
scoped = vars_ + '\n'.join(keep) + '\n#todo .tsec{border-top:1px solid var(--line);padding-top:10px;margin-top:10px}\n#todo .tsec:first-of-type{border-top:none;margin-top:0;padding-top:0}\n' \
         '@media (max-width:480px){#todo li{grid-template-columns:22px 1fr} #todo li .due{grid-column:2;justify-self:start} #todo li .body{grid-column:2}}'

main = re.search(r'<main[^>]*>(.*)</main>', todo, re.S).group(1)
upd = re.search(r'<header>.*?<p>(.*?)</p>', todo, re.S).group(1)
bar = re.search(r'<div class="bar">.*?</button>\s*</div>', main, re.S).group(0)
secs = re.findall(r'<section>(.*?)</section>', main, re.S)
inner = '\n'.join(f'<div class="tsec">{s}</div>' for s in secs)
script = re.search(r'<script>(.*?)</script>', todo, re.S).group(1).replace("document.querySelectorAll('li input", "document.querySelectorAll('#todo li input")

block = f'''<!--TODO-START-->
<style>{scoped}</style>
<section id="todo">
  <h2>Todo（小山さんがやること）</h2>
  <p class="sub">{upd}。チェックはこの端末のブラウザに保存されます。</p>
  {bar}
  {inner}
</section>
<script>{script}</script>
<!--TODO-END-->'''
rep = re.sub(r'<!--TODO-START-->.*?<!--TODO-END-->\n?', '', rep, flags=re.S)
m = re.search(r'(<section class="urgent">.*?</section>\n?)', rep, re.S)
if m:
    rep = rep[:m.end()] + block + '\n' + rep[m.end():]
else:
    rep = rep.replace('<main', '<main', 1)
    i = rep.index('>', rep.index('<main')) + 1
    rep = rep[:i] + '\n' + block + rep[i:]
open(rep_p, 'w', encoding='utf-8').write(rep)
print('merged', len(secs), 'sections')
