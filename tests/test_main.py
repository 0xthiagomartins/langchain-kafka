from src.client import RemoteRunnable


def main():
    client = RemoteRunnable(timeout=60)  # Set timeout as needed

    try:
        # Example invoke
        data = {"input": "Hello, LangChain!"}
        invoke_result = client.invoke(data)
        print("Invoke Result:", invoke_result)

        # Example batch
        data_list = [
            {"input": "First input"},
            {"input": "Second input"},
            {"input": "Third input"},
        ]
        batch_result = client.batch(data_list)
        print("Batch Result:", batch_result)

        # Example stream
        stream_data = {"input": "Stream this input"}
        stream_result = client.stream(stream_data)
        print("Stream Result:", stream_result)

    except Exception as e:
        print("An error occurred:", str(e))
    finally:
        client.close()


if __name__ == "__main__":
    main()
