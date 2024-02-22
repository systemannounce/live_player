#include <iostream>
#include <string>
#pragma comment( linker, "/subsystem:\"windows\" /entry:\"mainCRTStartup\"" ) // 尝试隐藏控制台

void vlc(const std::string& path_c, const std::string& url_c) {
    std::string path = path_c;
    std::string url = url_c;
    std::string command = "";
    path.resize(path.size() - 16);
    url = url.substr(6);

    command += path;
    command += "vlc.exe -vv --extraintf=logger ";
    command += url;
    std::cout << command.c_str() << std::endl;
    system(command.c_str());
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Error: No URL provided." << std::endl;
        return EXIT_FAILURE;
    }
    vlc(argv[0], argv[1]);
    return EXIT_SUCCESS;
}

