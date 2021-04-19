# qiita_f52c0841775f9fc4d0c5_owntracks

このプロジェクトには、SAM CLI を使用して展開できるサーバーレス アプリケーションのソース コードとサポート ファイルが含まれています。これには、次のファイルとフォルダが含まれます。

- hello_world - アプリケーションの Lambda 関数のコード。
- events - 関数の呼び出しに使用できる呼び出しイベント。
- template.yaml - アプリケーションの AWS リソースを定義するテンプレート。

## サンプル アプリケーションをデプロイする

サーバーレスアプリケーションモデルコマンドラインインターフェース (SAM CLI) は、Lambda アプリケーションを構築およびテストするための機能を追加する AWS CLI の拡張機能です。これは、Lambda を使用して、Lambda に一致する Amazon Linux 環境で関数を実行します。また、アプリケーションのビルド環境と API をエミュレートすることもできます。

SAM CLI を使用するには、次のツールが必要です。

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

アプリケーションをビルドしてデプロイするには、シェルで次のコードを実行します。

```bash
sam build
sam deploy
```

最初のコマンドは、アプリケーションのソースをビルドします。2 番目のコマンドは、一連のプロンプトを使用してアプリケーションをパッケージ化して AWS にデプロイします。

## SAM CLI を使用してローカルでビルドおよびテストする

コマンドを使用してアプリケーションをビルドします。

```bash
sam build --use-container
```

SAM CLI は で定義された依存関係をインストールし、展開パッケージを作成し、フォルダーに保存します。

テストイベントで直接呼び出して、単一の関数をテストします。イベントは、関数がイベント ソースから受け取る入力を表す JSON ドキュメントです。テスト イベントは、このプロジェクトのフォルダーに含まれます。

次の sam local invoke コマンドを使用し関数をローカルで実行します。

```bash
sam local invoke HelloWorldFunction --event events/event_is_not_u.json
sam local invoke HelloWorldFunction --event events/event_is_u.json
```

## Cleanup

作成したサンプルアプリケーションを削除するには、AWS CLI を使用します。スタック名にプロジェクト名を使用した場合、次のコードを実行できます。

```bash
aws cloudformation delete-stack --stack-name to-timestream
```

## Resources

SAM 仕様、SAM CLI、およびサーバーレスアプリケーションの概念の概要については、AWS SAM [開発者ガイド](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) を参照してください。
