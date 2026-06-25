# 讀取檔案，找到 ## 參考文獻 區塊，以排序後的版本取代
import re

path = r'c:\Users\admin\dev\umamusume-information-platform\論文_程式執行過程與結果.md'

with open(path, encoding='utf-8') as f:
    content = f.read()

# ── 新的排序後參考文獻區塊 ────────────────────────────
sorted_refs = """\
## 參考文獻

> 依 APA 第 7 版（American Psychological Association, 2020）格式，按第一作者姓氏或機構名稱英文字母順序排列。

\tAmerican Psychological Association. (2020). Publication manual of the American Psychological Association (7th ed.). https://doi.org/10.1037/0000165-000

\tAnthropic. (2024). *Claude's constitution* [Technical report]. Anthropic. https://www.anthropic.com/research/claudes-constitution

\tAnthropic. (2025). *Claude Sonnet 4.6* [Large language model]. Anthropic. https://www.anthropic.com/claude

\tAnthropic. (2026). Claude API (Models: Claude 4.8 Opus, Claude 4.6 Sonnet, Claude 4.5 Haiku) [API Service]. https://docs.anthropic.com/

\tBai, Y., Jones, A., Ndousse, K., Askell, A., Chen, A., DasSarma, N., Drain, D., Fort, S., Ganguli, D., Henighan, T., Joseph, N., Kadavath, S., Kernion, J., Conerly, T., El-Showk, S., Elhage, N., Hatfield-Dodds, Z., Hernandez, D., Hume, T., … Kaplan, J. (2022). Training a helpful and harmless assistant with reinforcement learning from human feedback. *arXiv preprint arXiv:2204.05862*. https://doi.org/10.48550/arXiv.2204.05862

\tBahamut Online Ltd. (2025). 賽馬娘 Pretty Derby 哈啦板 [線上論壇]. https://forum.gamer.com.tw/B.php?bsn=34421

\tBilibili Inc. (2025). 賽馬娘 Pretty Derby 繁中版 BWIKI [Wiki 平台]. https://wiki.biligame.com/umamusume/

\tBoettiger, C. (2015). An introduction to Docker for reproducible research. *ACM SIGOPS Operating Systems Review*, *49*(1), 71–79. https://doi.org/10.1145/2723872.2723882

\tBootstrap Team. (2024). Bootstrap: The world's most popular front-end open source toolkit (Version 5.3) [Software]. GitHub. https://github.com/twbs/bootstrap

\tBrown, T., Mann, B., Ryder, N., Subbiah, M., Kaplan, J. D., Dhariwal, P., Neelakantan, A., Shyam, P., Sastry, G., Askell, A., Agarwal, S., Herbert-Voss, A., Krueger, G., Henighan, T., Child, R., Ramesh, A., Ziegler, D., Wu, J., Winter, C., … Amodei, D. (2020). Language models are few-shot learners. *Advances in Neural Information Processing Systems*, *33*, 1877–1901. https://proceedings.neurips.cc/paper/2020/hash/1457c0d6bfcb4967418bfb8ac142f64a-Abstract.html

\tChart.js Contributors. (2024). Chart.js: Simple yet flexible JavaScript charting library (Version 4.x) [Software]. GitHub. https://github.com/chartjs/Chart.js

\tChase, H. (2022). *LangChain* (Version 1.3.1) [Software]. GitHub. https://github.com/langchain-ai/langchain

\tChollet, F. (2021). Deep learning with Python (2nd ed.). Manning Publications.

\tCygames, Inc. (2021). 賽馬娘 Pretty Derby [行動遊戲]. Cygames. https://umamusume.jp/

\tDevlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. In *Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies*, *1*, 4171–4186. https://doi.org/10.18653/v1/N19-1423

\tDjango Software Foundation. (2025). *Django documentation: Version 5.2* [Software documentation]. https://docs.djangoproject.com/en/5.2/

\tDocker, Inc. (2024). *Docker documentation: Docker Compose* [Software documentation]. https://docs.docker.com/compose/

\tGéron, A. (2022). Hands-on machine learning with Scikit-Learn, Keras, and TensorFlow: Concepts, tools, and techniques to build intelligent systems (3rd ed.). O'Reilly Media.

\tGoodfellow, I., Bengio, Y., & Courville, A. (2016). Deep learning. MIT Press. https://www.deeplearningbook.org/

\tGoogle. (2026). Gemini API (Models: Gemini 3.1 Pro, Gemini 3.5 Flash, Gemini 3.1 Flash-Lite) [API Service]. https://ai.google.dev/docs

\tGoogle DeepMind. (2025). *Gemini 3.5 Flash* [Large language model]. Google. https://deepmind.google/technologies/gemini/

\tGoogle LLC. (2024). YouTube Data API v3 reference [API documentation]. Google Developers. https://developers.google.com/youtube/v3/docs

\tGoogle LLC. (2026). Gemini API (Models: Gemini 3.1 Pro, Gemini 3.5 Flash, Gemini 3.1 Flash-Lite) [API Service]. Google AI for Developers. https://ai.google.dev/docs

\tGrönholm, A. (2024). APScheduler: Advanced Python scheduler (Version 3.11.2) [Software]. GitHub. https://github.com/agronholm/apscheduler

\tGunicorn Contributors. (2024). *Gunicorn: Python WSGI HTTP server for UNIX* (Version 23.0) [Software]. GitHub. https://github.com/benoitc/gunicorn

\tJcvergara22. (2024). django-apscheduler: APScheduler integration for the Django web framework (Version 0.7.0) [Software]. GitHub. https://github.com/jcvergara22/django-apscheduler

\tJohnson, J., Douze, M., & Jégou, H. (2021). Billion-scale similarity search with GPUs. *IEEE Transactions on Big Data*, *7*(3), 535–547. https://doi.org/10.1109/TBDATA.2019.2921572

\tLangChain AI. (2024). *LangGraph: Build stateful, multi-actor applications with LLMs* (Version 1.2.0) [Software]. GitHub. https://github.com/langchain-ai/langgraph

\tLewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems*, *33*, 9459–9474. https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html

\tLewin, D. (2023). Marked: A markdown parser and compiler built for speed (Version 12.x) [Software]. GitHub. https://github.com/markedjs/marked

\tLiu, B. (2012). *Sentiment analysis and opinion mining*. Morgan & Claypool Publishers. https://doi.org/10.2200/S00416ED1V01Y201204HLT016

\tMcKinney, W. (2010). Data structures for statistical computing in Python. In *Proceedings of the 9th Python in Science Conference*, 445, 51–56. https://doi.org/10.25080/Majora-92bf1922-00a

\tMerkel, D. (2014). Docker: Lightweight Linux containers for consistent development and deployment. *Linux Journal*, *2014*(239), Article 2. https://www.linuxjournal.com/content/docker-lightweight-linux-containers-consistent-development-and-deployment

\tMeta AI Research. (2024). *FAISS: A library for efficient similarity search and clustering of dense vectors* (Version 1.14.2) [Software]. GitHub. https://github.com/facebookresearch/faiss

\tNandini, D., Sumathy, R., & Vijayalakshmi, A. (2023). Sentiment analysis in social media using machine learning techniques: A survey. *International Journal of Intelligent Systems and Applications in Engineering*, *11*(4), 430–444. https://ijisae.org/index.php/IJISAE/article/view/3640

\tNginx, Inc. (2025). *Nginx documentation* [Software documentation]. https://nginx.org/en/docs/

\tOAI / Cursor. (2026). Codex 5.3 Model Environment and Composer 2 Workspace [Computer Software]. https://www.cursor.com/

\tpandas development team, The. (2024). *pandas: Powerful Python data analysis toolkit* (Version 2.x) [Software]. Zenodo. https://doi.org/10.5281/zenodo.3509134

\tPang, B., & Lee, L. (2008). Opinion mining and sentiment analysis. *Foundations and Trends® in Information Retrieval*, *2*(1–2), 1–135. https://doi.org/10.1561/1500000011

\tRapptz, D. (2024). discord.py: An API wrapper for Discord written in Python (Version 2.4.0) [Software]. GitHub. https://github.com/Rapptz/discord.py

\tReimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In *Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing*, 3982–3992. https://doi.org/10.18653/v1/D19-1410

\tReitz, K., & Schlusser, T. (2016). *The Hitchhiker's guide to Python: Best practices for development*. O'Reilly Media.

\tRichardson, L. (2007). *Beautiful Soup* [Software]. https://www.crummy.com/software/BeautifulSoup/

\tRossum, G. van, & Drake, F. L. (2009). *Python 3 reference manual*. Python Software Foundation. https://docs.python.org/3/

\tSchick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Hambro, E., Zettlemoyer, L., Cancedda, N., & Scialom, T. (2023). Toolformer: Language models can teach themselves to use tools. *Advances in Neural Information Processing Systems*, *36*, 68539–68551. https://proceedings.neurips.cc/paper_files/paper/2023/hash/d842425e4bf79ba039352da0f658a906-Abstract-Conference.html

\tSun, C., Qiu, X., Xu, Y., & Huang, X. (2019). How to fine-tune BERT for text classification? In *China National Conference on Chinese Computational Linguistics*, 194–206. https://doi.org/10.1007/978-3-030-32381-3_16

\tSun, J., & Sun, M. (2012). *jieba: Chinese word segmentation module* [Software]. GitHub. https://github.com/fxsjy/jieba

\tTeam, G., Anil, R., Borgeaud, S., Wu, Y., Alayrac, J.-B., Yu, J., Soricut, R., Schalkwyk, J., Dai, A. M., Hauth, A., Millican, K., Silver, D., Petrov, S., Johnson, M., Antonoglou, I., Schrittwieser, J., Glaese, A., Chen, J., Pitler, E., … Kavukcuoglu, K. (2023). Gemini: A family of highly capable multimodal models. *arXiv preprint arXiv:2312.11805*. https://doi.org/10.48550/arXiv.2312.11805

\tVaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. *Advances in Neural Information Processing Systems*, *30*, 5998–6008. https://proceedings.neurips.cc/paper/2017/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html

\tWang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., Zhang, J., Chen, Z., Tang, J., Chen, X., Lin, Y., Zhao, W. X., Wei, Z., & Wen, J.-R. (2024). A survey on large language model based autonomous agents. *Frontiers of Computer Science*, *18*(6), Article 186345. https://doi.org/10.1007/s11704-024-40231-1

\tWei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., & Zhou, D. (2022). Chain-of-thought prompting elicits reasoning in large language models. *Advances in Neural Information Processing Systems*, *35*, 24824–24837. https://proceedings.neurips.cc/paper_files/paper/2022/hash/9d5609613524ecf4f15af0f7b31abca4-Abstract-Conference.html

\tYao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. In *The Eleventh International Conference on Learning Representations*. https://openreview.net/forum?id=WE_vluYUL-X

\tZhao, W. X., Zhou, K., Li, J., Tang, T., Wang, X., Hou, Y., Min, Y., Zhang, B., Zhang, J., Dong, Z., Du, Y., Yang, C., Chen, Y., Chen, Z., Jiang, J., Ren, R., Li, Y., Tang, X., Liu, Z., … Wen, J.-R. (2023). A survey of large language models. *arXiv preprint arXiv:2303.18223*. https://doi.org/10.48550/arXiv.2303.18223"""

# 用正規表達式取代從 ## 參考文獻 到檔案結尾（不含最後的版本資訊行）
# 找到 ## 參考文獻 的位置
ref_start = content.find('## 參考文獻')
tail_marker = '\n---\n\n*本報告撰寫日期'
tail_pos = content.find(tail_marker, ref_start)

if ref_start == -1:
    print('ERROR: 找不到 ## 參考文獻')
elif tail_pos == -1:
    # 參考文獻到檔尾
    new_content = content[:ref_start] + sorted_refs + '\n'
else:
    new_content = content[:ref_start] + sorted_refs + '\n' + content[tail_pos:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Done. Lines:', new_content.count('\n'))
