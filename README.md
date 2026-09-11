*기본 세팅(새로운 기기에서 git 시작하기)

1: git을 설치한다 (pull할때 기본을 merge로 할지, rebase로 할지 고르는 거 있는데 협업 염두하면 merge로 하는 게 좋을듯

2: github에 올리고 싶은 폴더에 우클릭해서 bash 창을 연다 - git init

3: 
git config --global user.email "yyggh337@gmail.com"

git config --global user.name "KU_CS_HTG" 이름과 이메일을 등록

4: github repository를 만들고 주소를 복사해둔다

5: git remote add origin https://github.com/KU-CS-HTG/LG-CNS-KG-Project-1.git
이런 식으로 repository와 연결

6: git remote -v로 잘 연결되었는지 확인

*깃허브 저장소 내용 pull하기(다른 사람이 올려놓은 최신 코드를 먼저 받아오고, 그걸 업데이트해야 각자 사용하는 코드의 버전이 달라지는 것을 막을 수 있음)
git pull origin main

*업데이트한 내용 push하기(자신이 업데이트한 내용을 github에 올려서 이게 최신 버전이라고 다른 팀원들에게 알리기)

1: git에 있는 거(다른 기기에서 repository 업데이트 해놓은 경우) 먼저 pull하고 업데이트해야 함
까먹었다면 일일이 대조하면서 추가된 파일 다 빼놓고 pull할 수밖에 없음

2: git add . 

git commit -m “20260909-2” 이런 식으로 commit message 작성

3: git push -u origin main
