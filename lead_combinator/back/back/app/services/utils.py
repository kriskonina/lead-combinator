import aiofiles


async def read_last_line(filepath: str) -> str:
    newline_chars = {"\n", "\r\n", "\r"}
    chunk_size = 4096  # Read in chunks of 4KB
    last_line = ""
    async with aiofiles.open(filepath, "rb") as f:
        await f.seek(0, 2)  # Move to the end of the file
        file_size = await f.tell()
        for pos in range(file_size, 0, -chunk_size):
            if pos < chunk_size:
                chunk_size = pos
            await f.seek(pos - chunk_size, 0)
            chunk = await f.read(chunk_size)
            # Decode binary to string; adjust encoding as needed
            chunk_str = chunk.decode("utf-8", errors="ignore")
            lines = chunk_str.splitlines()
            if last_line:
                if chunk_str[-1] not in newline_chars:
                    lines[-1] += last_line
                else:
                    lines.append(last_line)
            if len(lines) > 1:
                return lines[-1]
            last_line = lines[0]
        return last_line[0]  # Return the last line found
